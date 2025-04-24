from flask import request, jsonify, render_template, redirect, url_for
import requests
from datetime import datetime
from models import db, Ticket

# Initialize routes with Flask app and event service URL
def init_routes(app, event_service_url):
    # --- Helper Functions ---
    
    def get_event_details(event_id):
        """Fetch event details from Event Service"""
        url = f"{event_service_url}/events/{event_id}"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error fetching event {event_id}: {e}")
            status_code = getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500
            error_msg = "Error connecting to Event Service" if status_code != 404 else "Event not found"
            return None, (error_msg, status_code)

    def update_event_tickets(event_id, ticket_count, operation):
        """Update available tickets count in Event Service"""
        url = f"{event_service_url}/events/{event_id}/tickets"
        try:
            response = requests.put(
                url,
                json={"ticket_count": ticket_count, "operation": operation},
                timeout=5
            )
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error updating tickets for event {event_id}: {e}")
            error_msg = "Error connecting to Event Service"
            status_code = 500
            
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                if status_code == 400:
                    try:
                        error_msg = e.response.json().get('error', error_msg)
                    except:
                        pass
                elif status_code == 404:
                    error_msg = "Event not found"
            
            return None, (error_msg, status_code)
    
    # --- Web Routes ---
    
    # Home page - shows all tickets
    @app.route('/')
    def index():
        tickets = Ticket.query.all()
        tickets_with_events = []
        
        for ticket in tickets:
            ticket_data = ticket.to_dict()
            # Try to fetch event details for each ticket
            event_details, _ = get_event_details(ticket.event_id)
            if event_details:
                ticket_data['event'] = event_details
            tickets_with_events.append(ticket_data)
        
        return render_template('index.html', tickets=tickets_with_events)
    
    # Ticket detail page
    @app.route('/tickets/<int:ticket_id>/view')
    def get_ticket_page(ticket_id):
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return render_template('index.html', error="Ticket not found", tickets=[])
        
        ticket_data = ticket.to_dict()
        # Try to fetch event details
        event_details, _ = get_event_details(ticket.event_id)
        if event_details:
            ticket_data['event'] = event_details
        
        return render_template('ticket_detail.html', ticket=ticket_data)
    
    # Buy ticket form page
    @app.route('/buy-ticket')
    def buy_ticket_page():
        event_id = request.args.get('event_id')
        if not event_id:
            return render_template('index.html', error="Event ID is required", tickets=[])
        
        # Fetch event details
        event_details, error = get_event_details(event_id)
        if error:
            return render_template('index.html', error=error[0], tickets=[])
        
        return render_template('buy_ticket.html', event=event_details)
    
    # Create ticket form submission
    @app.route('/buy-ticket', methods=['POST'])
    def create_ticket_web():
        try:
            event_id = request.form.get('event_id')
            customer_name = request.form.get('customer_name')
            customer_email = request.form.get('customer_email')
            quantity = request.form.get('quantity')
            
            # Validate required fields
            if not all([event_id, customer_name, customer_email, quantity]):
                return render_template('buy_ticket.html', error="All fields are required")
            
            # Validate event exists and has sufficient tickets
            event_details, error = get_event_details(event_id)
            if error:
                return render_template('buy_ticket.html', error=error[0])
            
            quantity = int(quantity)
            if quantity <= 0:
                return render_template('buy_ticket.html', event=event_details, error="Quantity must be greater than zero")
            
            if quantity > event_details['available_tickets']:
                return render_template('buy_ticket.html', event=event_details, error="Not enough tickets available")
            
            # Set price based on the event's price_per_ticket or fallback to default
            price_per_ticket = event_details.get('price_per_ticket', 100.00)
            total_price = price_per_ticket * quantity
            
            # Reserve tickets from the event
            update_result, error = update_event_tickets(
                event_id, 
                quantity, 
                'reserve'
            )
            
            if error:
                return render_template('buy_ticket.html', event=event_details, error=error[0])
            
            # Create ticket record
            new_ticket = Ticket(
                event_id=int(event_id),
                customer_name=customer_name,
                customer_email=customer_email,
                quantity=quantity,
                total_price=total_price,
                status='RESERVED'
            )
            
            db.session.add(new_ticket)
            db.session.commit()
            
            return redirect(url_for('get_ticket_page', ticket_id=new_ticket.id))
        except Exception as e:
            return render_template('buy_ticket.html', error=str(e))
    
    # Update ticket status
    @app.route('/tickets/<int:ticket_id>/status', methods=['POST'])
    def update_ticket_status_web(ticket_id):
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return redirect(url_for('index'))
        
        status = request.form.get('status')
        if not status:
            return render_template('ticket_detail.html', ticket=ticket.to_dict(), error="Status is required")
        
        new_status = status.upper()
        valid_statuses = ['RESERVED', 'CONFIRMED', 'CANCELLED']
        
        if new_status not in valid_statuses:
            return render_template('ticket_detail.html', ticket=ticket.to_dict(), 
                                 error=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        # Handle status change logic
        if ticket.status == new_status:
            # No change needed
            return redirect(url_for('get_ticket_page', ticket_id=ticket.id))
        
        if ticket.status == 'CANCELLED' and new_status != 'CANCELLED':
            # Cannot un-cancel a ticket
            return render_template('ticket_detail.html', ticket=ticket.to_dict(), 
                                 error="Cannot change status of a cancelled ticket")
        
        # If cancelling a ticket, release the reserved tickets back to the event
        if new_status == 'CANCELLED' and ticket.status != 'CANCELLED':
            update_result, error = update_event_tickets(
                ticket.event_id,
                ticket.quantity,
                'release'
            )
            
            if error:
                return render_template('ticket_detail.html', ticket=ticket.to_dict(), error=error[0])
        
        # Update ticket status
        ticket.status = new_status
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        
        return redirect(url_for('get_ticket_page', ticket_id=ticket.id))
    
    # Delete ticket
    @app.route('/tickets/<int:ticket_id>/delete', methods=['POST'])
    def delete_ticket_web(ticket_id):
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return redirect(url_for('index'))
        
        # Only allow deletion of cancelled tickets to maintain integrity
        if ticket.status != 'CANCELLED':
            # First cancel the ticket to release the tickets back to the event
            update_result, error = update_event_tickets(
                ticket.event_id,
                ticket.quantity,
                'release'
            )
            
            if error:
                ticket_data = ticket.to_dict()
                event_details, _ = get_event_details(ticket.event_id)
                if event_details:
                    ticket_data['event'] = event_details
                return render_template('ticket_detail.html', ticket=ticket_data, error=error[0])
        
        db.session.delete(ticket)
        db.session.commit()
        
        return redirect(url_for('index'))
    
    # --- API Endpoints ---
    
    # Get all tickets
    @app.route('/tickets', methods=['GET'])
    def get_tickets():
        # Optional filter by event_id
        event_id = request.args.get('event_id')
        
        if event_id:
            tickets = Ticket.query.filter_by(event_id=event_id).all()
        else:
            tickets = Ticket.query.all()
        
        return jsonify([ticket.to_dict() for ticket in tickets]), 200
    
    # Get a single ticket
    @app.route('/tickets/<int:ticket_id>', methods=['GET'])
    def get_ticket(ticket_id):
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Get event details to include in the response
        event_details, error = get_event_details(ticket.event_id)
        
        response = ticket.to_dict()
        if event_details:
            response['event'] = event_details
        else:
            response['event'] = {'error': error[0]} if error else {'error': 'Event details not available'}
        
        return jsonify(response), 200
    
    # Create a new ticket
    @app.route('/tickets', methods=['POST'])
    def create_ticket():
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        
        required_fields = ['event_id', 'customer_name', 'customer_email', 'quantity']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Field '{field}' is required"}), 400
        
        # Validate event exists and has sufficient tickets
        event_details, error = get_event_details(data['event_id'])
        if error:
            return jsonify({"error": error[0]}), error[1]
        
        if data['quantity'] <= 0:
            return jsonify({"error": "Quantity must be greater than zero"}), 400
        
        if data['quantity'] > event_details['available_tickets']:
            return jsonify({"error": "Not enough tickets available"}), 400
        
        # Get price from event details or use default
        price_per_ticket = event_details.get('price_per_ticket', 100.00)
        total_price = price_per_ticket * data['quantity']
        
        # Reserve tickets from the event
        update_result, error = update_event_tickets(
            data['event_id'], 
            data['quantity'], 
            'reserve'
        )
        
        if error:
            return jsonify({"error": error[0]}), error[1]
        
        # Create ticket record
        new_ticket = Ticket(
            event_id=data['event_id'],
            customer_name=data['customer_name'],
            customer_email=data['customer_email'],
            quantity=data['quantity'],
            total_price=total_price,
            status='RESERVED'
        )
        
        db.session.add(new_ticket)
        db.session.commit()
        
        response = new_ticket.to_dict()
        response['event'] = event_details
        
        return jsonify(response), 201
    
    # Update ticket status
    @app.route('/tickets/<int:ticket_id>/status', methods=['PUT'])
    def update_ticket_status(ticket_id):
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        
        if 'status' not in data:
            return jsonify({"error": "Status is required"}), 400
        
        new_status = data['status'].upper()
        valid_statuses = ['RESERVED', 'CONFIRMED', 'CANCELLED']
        
        if new_status not in valid_statuses:
            return jsonify({"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400
        
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Handle status change logic
        if ticket.status == new_status:
            # No change needed
            return jsonify(ticket.to_dict()), 200
        
        if ticket.status == 'CANCELLED' and new_status != 'CANCELLED':
            # Cannot un-cancel a ticket
            return jsonify({"error": "Cannot change status of a cancelled ticket"}), 400
        
        # If cancelling a ticket, release the reserved tickets back to the event
        if new_status == 'CANCELLED' and ticket.status != 'CANCELLED':
            update_result, error = update_event_tickets(
                ticket.event_id,
                ticket.quantity,
                'release'
            )
            
            if error:
                return jsonify({"error": error[0]}), error[1]
        
        # Update ticket status
        ticket.status = new_status
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(ticket.to_dict()), 200
    
    # Delete a ticket
    @app.route('/tickets/<int:ticket_id>', methods=['DELETE'])
    def delete_ticket(ticket_id):
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Only allow deletion of cancelled tickets to maintain integrity
        if ticket.status != 'CANCELLED':
            # First cancel the ticket to release the tickets back to the event
            update_result, error = update_event_tickets(
                ticket.event_id,
                ticket.quantity,
                'release'
            )
            
            if error:
                return jsonify({"error": error[0]}), error[1]
            
            # Mark the ticket as cancelled before deletion
            ticket.status = 'CANCELLED'
            ticket.updated_at = datetime.utcnow()
            db.session.commit()
        
        db.session.delete(ticket)
        db.session.commit()
        
        return jsonify({'message': 'Ticket deleted successfully'}), 200
