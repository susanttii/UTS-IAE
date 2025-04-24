from flask import request, jsonify, render_template, redirect, url_for
from datetime import datetime
from models import db, Event, Venue

# Initialize routes with Flask app
def init_routes(app):
    # --- Web Routes ---
    
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
                if price_per_ticket <= 0:
                    raise ValueError("Price must be greater than zero")
            except ValueError as e:
                venues = Venue.query.all()
                return render_template('create_event.html', 
                                      error=str(e),
                                      venues=[venue.to_dict() for venue in venues])
            
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
            price_per_ticket = request.form.get('price_per_ticket', 100.00)
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
                if price_per_ticket <= 0:
                    raise ValueError("Price must be greater than zero")
            except ValueError as e:
                return render_template('edit_event.html', 
                                      event=event.to_dict(),
                                      error=str(e))
            
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

    # --- API Routes ---
    
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

    # Create an event
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

    # Update an event
    @app.route('/events/<int:event_id>', methods=['PUT'])
    def update_event(event_id):
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        event = Event.query.get(event_id)
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        data = request.get_json()
        
        # Update fields if provided
        if 'name' in data:
            event.name = data['name']
        
        if 'description' in data:
            event.description = data['description']
        
        if 'event_date' in data:
            try:
                event.event_date = datetime.fromisoformat(data['event_date'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)."}), 400
        
        if 'venue' in data:
            event.venue = data['venue']
        
        if 'total_tickets' in data:
            # Calculate tickets sold
            tickets_sold = event.total_tickets - event.available_tickets
            event.total_tickets = data['total_tickets']
            # Adjust available tickets
            event.available_tickets = max(0, event.total_tickets - tickets_sold)
        
        if 'price_per_ticket' in data:
            event.price_per_ticket = data['price_per_ticket']
        
        if 'image_url' in data:
            event.image_url = data['image_url']
        
        event.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(event.to_dict()), 200

    # Delete an event
    @app.route('/events/<int:event_id>', methods=['DELETE'])
    def delete_event(event_id):
        event = Event.query.get(event_id)
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({'message': 'Event deleted successfully'}), 200

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

    # Venues API
    @app.route('/venues', methods=['GET'])
    def get_venues():
        venues = Venue.query.all()
        return jsonify([venue.to_dict() for venue in venues]), 200

    @app.route('/venues/<int:venue_id>', methods=['GET'])
    def get_venue(venue_id):
        venue = Venue.query.get(venue_id)
        if not venue:
            return jsonify({'error': 'Venue not found'}), 404
        
        return jsonify(venue.to_dict()), 200

    # Create a venue
    @app.route('/venues', methods=['POST'])
    def create_venue():
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        
        required_fields = ['name', 'address', 'city', 'capacity']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Field '{field}' is required"}), 400
        
        # Create new venue
        new_venue = Venue(
            name=data['name'],
            address=data['address'],
            city=data['city'],
            capacity=data['capacity'],
            description=data.get('description', '')
        )
        
        db.session.add(new_venue)
        db.session.commit()
        
        return jsonify(new_venue.to_dict()), 201
