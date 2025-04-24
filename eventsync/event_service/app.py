import os
import sqlite3
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize Flask application
app = Flask(__name__)

# Configure database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'event_data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Event Model
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_date = db.Column(db.DateTime, nullable=False)
    venue = db.Column(db.String(100), nullable=False)
    total_tickets = db.Column(db.Integer, nullable=False)
    available_tickets = db.Column(db.Integer, nullable=False)
    price_per_ticket = db.Column(db.Float, default=100.00)
    image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'event_date': self.event_date.isoformat(),
            'venue': self.venue,
            'total_tickets': self.total_tickets,
            'available_tickets': self.available_tickets,
            'price_per_ticket': self.price_per_ticket,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# Venue Model (untuk dropdown venues)
class Venue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'capacity': self.capacity,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        }

# Create database tables
with app.app_context():
    db.create_all()
    
    # Create default venue if none exists
    if Venue.query.first() is None:
        default_venue = Venue(
            name="Main Hall",
            address="Jl. Sudirman No. 123",
            city="Jakarta",
            capacity=1000,
            description="Our main event venue"
        )
        db.session.add(default_venue)
        db.session.commit()
    
    print("Event Service: Database initialized.")

# Home page - shows all events
@app.route('/')
def index():
    events = Event.query.all()
    return render_template('index.html', events=[event.to_dict() for event in events])

# Event detail page
@app.route('/events/<int:event_id>/view')
def get_event_page(event_id):
    event = Event.query.get(event_id)
    if not event:
        return render_template('index.html', error="Event not found", events=[])
    return render_template('event_detail.html', event=event.to_dict())

# Create event form
@app.route('/create', methods=['GET'])
def create_event_form():
    venues = Venue.query.all()
    return render_template('create_event.html', venues=[venue.to_dict() for venue in venues])

# Create event form submission
@app.route('/create', methods=['POST'])
def create_event_web():
    try:
        name = request.form.get('name')
        description = request.form.get('description') 
        event_date_str = request.form.get('event_date')
        venue = request.form.get('venue')
        total_tickets = request.form.get('total_tickets')
        price_per_ticket = request.form.get('price_per_ticket', 100.00)
        image_url = request.form.get('image_url', '')
        
        # Validate required fields
        if not all([name, event_date_str, venue, total_tickets]):
            venues = Venue.query.all()
            return render_template('create_event.html', 
                                  error="Required fields: name, event date, venue, and total tickets",
                                  venues=[venue.to_dict() for venue in venues])
        
        # Parse datetime
        try:
            event_date = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
        except ValueError:
            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                venues = Venue.query.all()
                return render_template('create_event.html', 
                                      error="Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM).",
                                      venues=[venue.to_dict() for venue in venues])
        
        # Parse integer values
        try:
            total_tickets = int(total_tickets)
            if total_tickets <= 0:
                raise ValueError("Total tickets must be greater than zero")
        except ValueError as e:
            venues = Venue.query.all()
            return render_template('create_event.html', 
                                  error=str(e),
                                  venues=[venue.to_dict() for venue in venues])
        
        # Parse price
        try:
            price_per_ticket = float(price_per_ticket)
            if price_per_ticket < 0:
                price_per_ticket = 100.00
        except (ValueError, TypeError):
            price_per_ticket = 100.00
        
        # Create new event
        new_event = Event(
            name=name,
            description=description,
            event_date=event_date,
            venue=venue,
            total_tickets=total_tickets,
            available_tickets=total_tickets,
            price_per_ticket=price_per_ticket,
            image_url=image_url
        )
        
        db.session.add(new_event)
        db.session.commit()
        
        return redirect(url_for('get_event_page', event_id=new_event.id))
    except Exception as e:
        venues = Venue.query.all()
        return render_template('create_event.html', 
                              error=str(e),
                              venues=[venue.to_dict() for venue in venues])

# Edit event form
@app.route('/events/<int:event_id>/edit', methods=['GET'])
def edit_event_form(event_id):
    event = Event.query.get(event_id)
    if not event:
        return redirect(url_for('index'))
    
    venues = Venue.query.all()
    return render_template('edit_event.html', 
                          event=event.to_dict(), 
                          venues=[venue.to_dict() for venue in venues])

# Edit event form submission
@app.route('/events/<int:event_id>/edit', methods=['POST'])
def edit_event_web(event_id):
    event = Event.query.get(event_id)
    if not event:
        return redirect(url_for('index'))
    
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        event_date_str = request.form.get('event_date')
        venue = request.form.get('venue')
        total_tickets = request.form.get('total_tickets')
        price_per_ticket = request.form.get('price_per_ticket', event.price_per_ticket)
        image_url = request.form.get('image_url', event.image_url)
        
        # Validate required fields
        if not all([name, event_date_str, venue, total_tickets]):
            return render_template('edit_event.html', 
                                  event=event.to_dict(),
                                  error="Required fields: name, event date, venue, and total tickets")
        
        # Parse datetime
        try:
            event_date = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
        except ValueError:
            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                return render_template('edit_event.html', 
                                      event=event.to_dict(),
                                      error="Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM).")
        
        # Parse integer values
        try:
            total_tickets = int(total_tickets)
            if total_tickets <= 0:
                raise ValueError("Total tickets must be greater than zero")
        except ValueError as e:
            return render_template('edit_event.html', 
                                  event=event.to_dict(),
                                  error=str(e))
        
        # Parse price
        try:
            price_per_ticket = float(price_per_ticket)
            if price_per_ticket < 0:
                price_per_ticket = 100.00
        except (ValueError, TypeError):
            price_per_ticket = 100.00
        
        # Calculate available tickets
        tickets_sold = event.total_tickets - event.available_tickets
        new_available = max(0, total_tickets - tickets_sold)
        
        # Update event
        event.name = name
        event.description = description
        event.event_date = event_date
        event.venue = venue
        event.total_tickets = total_tickets
        event.available_tickets = new_available
        event.price_per_ticket = price_per_ticket
        event.image_url = image_url
        event.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return redirect(url_for('get_event_page', event_id=event.id))
    except Exception as e:
        return render_template('edit_event.html', 
                              event=event.to_dict(),
                              error=str(e))

# Delete event
@app.route('/events/<int:event_id>/delete', methods=['POST'])
def delete_event_web(event_id):
    event = Event.query.get(event_id)
    if not event:
        return redirect(url_for('index'))
    
    db.session.delete(event)
    db.session.commit()
    
    return redirect(url_for('index'))

# --- API Endpoints ---

# Get all events
@app.route('/events', methods=['GET'])
def get_events():
    events = Event.query.all()
    return jsonify([event.to_dict() for event in events]), 200

# Get a single event
@app.route('/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    event = Event.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    return jsonify(event.to_dict()), 200

# Create an event (API)
@app.route('/events', methods=['POST'])
def create_event():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    required_fields = ['name', 'event_date', 'venue', 'total_tickets']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Field '{field}' is required"}), 400
    
    # Parse date
    try:
        event_date = datetime.fromisoformat(data['event_date'].replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)."}), 400
    
    # Create new event
    new_event = Event(
        name=data['name'],
        description=data.get('description', ''),
        event_date=event_date,
        venue=data['venue'],
        total_tickets=data['total_tickets'],
        available_tickets=data['total_tickets'],
        price_per_ticket=data.get('price_per_ticket', 100.00),
        image_url=data.get('image_url', '')
    )
    
    db.session.add(new_event)
    db.session.commit()
    
    return jsonify(new_event.to_dict()), 201

# Endpoint for Ticket Service to update available tickets
@app.route('/events/<int:event_id>/tickets', methods=['PUT'])
def update_available_tickets(event_id):
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    
    if 'ticket_count' not in data:
        return jsonify({"error": "ticket_count is required"}), 400
    
    ticket_count = int(data['ticket_count'])
    
    event = Event.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    # Check if operation is to reserve tickets
    if data.get('operation') == 'reserve':
        if ticket_count > event.available_tickets:
            return jsonify({'error': 'Not enough tickets available'}), 400
        
        event.available_tickets -= ticket_count
    # Operation is to release tickets (e.g., cancelled reservation)
    elif data.get('operation') == 'release':
        if event.available_tickets + ticket_count > event.total_tickets:
            return jsonify({'error': 'Cannot release more tickets than the total'}), 400
        
        event.available_tickets += ticket_count
    else:
        return jsonify({'error': 'Invalid operation. Use "reserve" or "release"'}), 400
    
    event.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'event_id': event.id,
        'available_tickets': event.available_tickets,
        'total_tickets': event.total_tickets
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
