import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()

# Initialize the Flask App
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# --- DATABASE CONFIGURATION ---
# The database URL is now loaded securely from the .env file
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)

# --- DATABASE MODELS ---
# These classes define the structure of your database tables.

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    # This creates a relationship so you can see all items from a supplier
    inventory_items = db.relationship('Inventory', backref='supplier', lazy=True, cascade="all, delete-orphan")

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact': self.contact,
            'email': self.email
        }

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'quantity': self.quantity,
            'price': self.price,
            'supplierId': self.supplier_id,
            'supplierName': self.supplier.name if self.supplier else None
        }

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orderIdString = db.Column(db.String(50), unique=True, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    totalCost = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Placed')
    # Foreign keys to link the order to an item and supplier
    item_id = db.Column(db.Integer, db.ForeignKey('inventory.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    
    # Relationships (optional, but good for accessing linked data)
    item = db.relationship('Inventory')
    supplier = db.relationship('Supplier')
    
    def to_json(self):
        return {
            'id': self.id,
            'orderIdString': self.orderIdString,
            'quantity': self.quantity,
            'totalCost': self.totalCost,
            'status': self.status,
            'itemId': self.item_id,
            'supplierId': self.supplier_id,
            'itemName': self.item.name if self.item else "Deleted Item",
            'supplierName': self.supplier.name if self.supplier else "Deleted Supplier"
        }

# --- RENDER THE FRONTEND ---
@app.route('/')
def index():
    # This now serves your main HTML page from the 'templates' folder
    return render_template('index.html')


# --- API ROUTES ---

# Endpoint to get all data when the app loads
@app.route('/api/state', methods=['GET'])
def get_initial_state():
    suppliers_list = [s.to_json() for s in Supplier.query.all()]
    inventory_list = [i.to_json() for i in Inventory.query.all()]
    orders_list = [o.to_json() for o in Order.query.all()]
    return jsonify({
        'suppliers': suppliers_list,
        'inventory': inventory_list,
        'orders': orders_list
    })

# --- Suppliers API ---
@app.route('/api/suppliers', methods=['POST'])
def add_supplier():
    data = request.get_json()
    new_supplier = Supplier(name=data['name'], contact=data['contact'], email=data['email'])
    db.session.add(new_supplier)
    db.session.commit()
    return jsonify(new_supplier.to_json()), 201

@app.route('/api/suppliers/<int:id>', methods=['DELETE'])
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    # Also delete orders associated with this supplier
    Order.query.filter_by(supplier_id=id).delete()
    db.session.delete(supplier)
    db.session.commit()
    return jsonify({'message': 'Supplier and related orders deleted'}), 200

# --- Inventory API ---
@app.route('/api/inventory', methods=['POST'])
def add_inventory_item():
    data = request.get_json()
    new_item = Inventory(
        name=data['name'],
        description=data['description'],
        quantity=data['quantity'],
        price=data['price'],
        supplier_id=data['supplierId']
    )
    db.session.add(new_item)
    db.session.commit()
    return jsonify(new_item.to_json()), 201

@app.route('/api/inventory/<int:id>', methods=['DELETE'])
def delete_inventory_item(id):
    item = Inventory.query.get_or_404(id)
    # Delete orders associated with this item
    Order.query.filter_by(item_id=id).delete()
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Item and related orders deleted'}), 200

# --- Orders API ---
@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    item_id = data['itemId']
    quantity = data['quantity']
    
    item = Inventory.query.get(item_id)
    if not item:
        return jsonify({'message': 'Item not found'}), 404
    if item.quantity < quantity:
        return jsonify({'message': 'Not enough stock'}), 400
        
    # Update item quantity
    item.quantity -= quantity
    
    new_order = Order(
        orderIdString=data['orderIdString'],
        item_id=data['itemId'],
        supplier_id=data['supplierId'],
        quantity=data['quantity'],
        totalCost=data['totalCost'],
        status='Placed'
    )
    db.session.add(new_order)
    db.session.commit()
    # The response includes the updated item quantity and the new order
    return jsonify({
        'order': new_order.to_json(), 
        'updatedItem': item.to_json()
    }), 201

@app.route('/api/orders/<int:id>', methods=['DELETE'])
def delete_order(id):
    order = Order.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    return jsonify({'message': 'Order deleted'}), 200


# Main entry point to run the app
if __name__ == '__main__':
    with app.app_context():
        # This creates the database tables if they don't exist
        db.create_all()
    app.run(debug=True)
