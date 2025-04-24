import os
import requests
import sqlite3
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize Flask application
app = Flask(__name__)

# Configure database
basedir = os.path.abspath(os.path.dirname(__file__))

# Asegurarse de que el directorio tiene permisos adecuados
db_path = os.path.join(basedir, 'ticket_data.db')

# Si la base de datos existe, asegurarse de que tiene permisos de escritura
if os.path.exists(db_path):
    os.chmod(db_path, 0o666)  # Dar permisos de lectura/escritura

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure Event Service URL
EVENT_SERVICE_URL = os.getenv('EVENT_SERVICE_URL', 'http://localhost:5001')

# Inicializar SQLAlchemy
db = SQLAlchemy(app)

# Modelo de Ticket
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # RESERVED, CONFIRMED, CANCELLED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'quantity': self.quantity,
            'total_price': self.total_price,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# Crear tablas de la base de datos
with app.app_context():
    db.create_all()
    print("Ticket Service: Database initialized.")

# ------ Funciones Auxiliares ------

def get_event(event_id):
    """Obtiene un evento del Event Service por su ID"""
    try:
        response = requests.get(f"{EVENT_SERVICE_URL}/events/{event_id}")
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException:
        return None

def check_ticket_availability(event_id, quantity):
    """Verifica si hay suficientes tickets disponibles para un evento"""
    event = get_event(event_id)
    if not event or not event.get('available_tickets'):
        return False, 0
    
    available = event['available_tickets']
    return available >= quantity, available

def reserve_tickets(event_id, quantity):
    """Solicita al Event Service reservar tickets para un evento"""
    try:
        response = requests.put(
            f"{EVENT_SERVICE_URL}/events/{event_id}/tickets",
            json={"ticket_count": quantity, "operation": "reserve"}
        )
        return response.status_code == 200
    except requests.RequestException:
        return False

def release_tickets(event_id, quantity):
    """Solicita al Event Service liberar tickets reservados"""
    try:
        response = requests.put(
            f"{EVENT_SERVICE_URL}/events/{event_id}/tickets",
            json={"ticket_count": quantity, "operation": "release"}
        )
        return response.status_code == 200
    except requests.RequestException:
        return False

# ------ Rutas Web ------

@app.route('/')
def index():
    tickets = Ticket.query.all()
    return render_template('index.html', tickets=[ticket.to_dict() for ticket in tickets])

@app.route('/tickets/<int:ticket_id>')
def get_ticket_page(ticket_id):
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return render_template('index.html', error="Ticket not found", tickets=[])
    
    # Obtener información del evento
    event = get_event(ticket.event_id)
    
    return render_template('ticket_detail.html', ticket=ticket.to_dict(), event=event)

@app.route('/buy-ticket')
def buy_ticket_form():
    event_id = request.args.get('event_id')
    if not event_id:
        return render_template('index.html', error="Event ID is required", tickets=[])
    
    event = get_event(event_id)
    if not event:
        return render_template('index.html', error="Event not found", tickets=[])
    
    return render_template('buy_ticket.html', event=event)

@app.route('/buy-ticket', methods=['POST'])
def buy_ticket():
    try:
        event_id = request.form.get('event_id')
        customer_name = request.form.get('customer_name')
        customer_email = request.form.get('customer_email')
        quantity_str = request.form.get('quantity')
        
        # Validar campos requeridos
        if not all([event_id, customer_name, customer_email, quantity_str]):
            return render_template('buy_ticket.html', 
                                  error="All fields are required",
                                  event=get_event(event_id))
        
        # Convertir a entero
        try:
            event_id = int(event_id)
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero")
        except ValueError as e:
            return render_template('buy_ticket.html', 
                                  error=str(e),
                                  event=get_event(event_id))
        
        # Verificar disponibilidad
        available, _ = check_ticket_availability(event_id, quantity)
        if not available:
            return render_template('buy_ticket.html', 
                                  error="Not enough tickets available",
                                  event=get_event(event_id))
        
        # Obtener información del evento para el precio
        event = get_event(event_id)
        if not event:
            return render_template('buy_ticket.html', 
                                  error="Event not found",
                                  event=None)
        
        # Calcular precio total
        price_per_ticket = event.get('price_per_ticket', 100.00)
        total_price = price_per_ticket * quantity
        
        # Reservar tickets
        reserved = reserve_tickets(event_id, quantity)
        if not reserved:
            return render_template('buy_ticket.html', 
                                  error="Failed to reserve tickets",
                                  event=event)
        
        # Crear ticket
        new_ticket = Ticket(
            event_id=event_id,
            customer_name=customer_name,
            customer_email=customer_email,
            quantity=quantity,
            total_price=total_price,
            status="RESERVED"
        )
        
        db.session.add(new_ticket)
        db.session.commit()
        
        return redirect(url_for('get_ticket_page', ticket_id=new_ticket.id))
    except Exception as e:
        return render_template('buy_ticket.html', 
                              error=str(e),
                              event=get_event(event_id))

@app.route('/tickets/<int:ticket_id>/status', methods=['POST'])
def update_ticket_status(ticket_id):
    new_status = request.form.get('status')
    
    if not ticket_id or not new_status:
        return redirect(url_for('index'))
    
    ticket = Ticket.query.get(int(ticket_id))
    if not ticket:
        return redirect(url_for('index'))
    
    # Si se cancela un ticket, liberar los tickets en el Event Service
    if new_status == "CANCELLED" and ticket.status != "CANCELLED":
        released = release_tickets(ticket.event_id, ticket.quantity)
        if not released:
            return render_template('ticket_detail.html', 
                                  ticket=ticket.to_dict(),
                                  event=get_event(ticket.event_id),
                                  error="Failed to release tickets")
    
    ticket.status = new_status
    ticket.updated_at = datetime.utcnow()
    db.session.commit()
    
    return redirect(url_for('get_ticket_page', ticket_id=ticket.id))

# Endpoint untuk form web updates
@app.route('/tickets/<int:ticket_id>/update', methods=['POST'])
def update_ticket_status_web(ticket_id):
    new_status = request.form.get('status')
    
    if not new_status:
        return redirect(url_for('get_ticket_page', ticket_id=ticket_id))
    
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return redirect(url_for('index'))
    
    # Jika tiket dibatalkan, bebaskan tiket di Event Service
    if new_status == "CANCELLED" and ticket.status != "CANCELLED":
        released = release_tickets(ticket.event_id, ticket.quantity)
        if not released:
            return render_template('ticket_detail.html', 
                                  ticket=ticket.to_dict(),
                                  event=get_event(ticket.event_id),
                                  error="Gagal membebaskan tiket")
    
    ticket.status = new_status
    ticket.updated_at = datetime.utcnow()
    db.session.commit()
    
    return redirect(url_for('get_ticket_page', ticket_id=ticket.id))

# ------ API Endpoints ------

# Endpoint dengan format README (/tickets)
@app.route('/tickets', methods=['GET'])
def get_tickets_compat():
    tickets = Ticket.query.all()
    return jsonify([ticket.to_dict() for ticket in tickets]), 200

# API endpoint dengan prefix (/api/tickets)
@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    tickets = Ticket.query.all()
    return jsonify([ticket.to_dict() for ticket in tickets]), 200

@app.route('/tickets/<int:ticket_id>', methods=['GET'])
def get_ticket_compat(ticket_id):
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    return jsonify(ticket.to_dict()), 200

@app.route('/api/tickets/<int:ticket_id>', methods=['GET'])
def get_ticket(ticket_id):
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    return jsonify(ticket.to_dict()), 200

@app.route('/tickets', methods=['POST'])
def create_ticket_compat():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    required_fields = ['event_id', 'customer_name', 'customer_email', 'quantity']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Field '{field}' is required"}), 400
    
    # Validar disponibilidad
    event_id = data['event_id']
    quantity = data['quantity']
    
    available, _ = check_ticket_availability(event_id, quantity)
    if not available:
        return jsonify({"error": "Not enough tickets available"}), 400
    
    # Obtener información del evento para el precio
    event = get_event(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    
    # Calcular precio total
    price_per_ticket = event.get('price_per_ticket', 100.00)
    total_price = price_per_ticket * quantity
    
    # Reservar tickets
    reserved = reserve_tickets(event_id, quantity)
    if not reserved:
        return jsonify({"error": "Failed to reserve tickets"}), 500
    
    # Crear ticket
    new_ticket = Ticket(
        event_id=event_id,
        customer_name=data['customer_name'],
        customer_email=data['customer_email'],
        quantity=quantity,
        total_price=total_price,
        status="RESERVED"
    )
    
    db.session.add(new_ticket)
    db.session.commit()
    
    return jsonify(new_ticket.to_dict()), 201

@app.route('/api/tickets', methods=['POST'])
def create_ticket():
    return create_ticket_compat()

@app.route('/tickets/<int:ticket_id>', methods=['PUT'])
def update_ticket_compat(ticket_id):
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    data = request.get_json()
    
    if 'status' in data:
        new_status = data['status']
        if new_status not in ["RESERVED", "CONFIRMED", "CANCELLED"]:
            return jsonify({"error": "Invalid status"}), 400
        
        # Si se cancela un ticket, liberar los tickets en el Event Service
        if new_status == "CANCELLED" and ticket.status != "CANCELLED":
            released = release_tickets(ticket.event_id, ticket.quantity)
            if not released:
                return jsonify({"error": "Failed to release tickets"}), 500
        
        ticket.status = new_status
    
    # No permitir actualizar otras propiedades una vez creado
    
    ticket.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(ticket.to_dict()), 200

# Endpoint específico para actualizar solo el status de un ticket
@app.route('/tickets/<int:ticket_id>/status', methods=['GET', 'PUT'])
def update_ticket_status_api(ticket_id):
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    # GET method untuk melihat status tiket
    if request.method == 'GET':
        event = get_event(ticket.event_id)
        return render_template('ticket_detail.html', ticket=ticket.to_dict(), event=event)
    
    # PUT method untuk update status
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    if 'status' not in data:
        return jsonify({"error": "Status field is required"}), 400
        
    new_status = data['status']
    if new_status not in ["RESERVED", "CONFIRMED", "CANCELLED"]:
        return jsonify({"error": "Invalid status"}), 400
    
    # Si se cancela un ticket, liberar los tickets en el Event Service
    if new_status == "CANCELLED" and ticket.status != "CANCELLED":
        released = release_tickets(ticket.event_id, ticket.quantity)
        if not released:
            return jsonify({"error": "Failed to release tickets"}), 500
    
    ticket.status = new_status
    ticket.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(ticket.to_dict()), 200

@app.route('/api/tickets/<int:ticket_id>', methods=['PUT'])
def update_ticket(ticket_id):
    return update_ticket_compat(ticket_id)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
