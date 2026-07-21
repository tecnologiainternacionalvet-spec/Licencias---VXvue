from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////data/licencias.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
API_SECRET = os.environ.get('API_SECRET', 'clave-secreta-cambiar')

db = SQLAlchemy(app)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    equipo_id = db.Column(db.String(100), unique=True, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    notas = db.Column(db.String(300), default='')

with app.app_context():
    db.create_all()

@app.after_request
def agregar_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Secret'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    return response

@app.route('/options', methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options(path=''):
    return '', 204

@app.route('/')
@app.route('/panel')
def panel():
    return send_from_directory('.', 'panel_admin.html')

def verificar_secret(req):
    return req.headers.get('X-API-Secret') == API_SECRET

# ─── ENDPOINT QUE CONSULTA EL AGENTE DEL CLIENTE ───────────────────────────
@app.route('/verificar', methods=['GET'])
def verificar():
    equipo_id = request.args.get('equipo_id', '')
    if not equipo_id:
        return jsonify({'activo': False, 'mensaje': 'ID de equipo requerido'}), 400
    cliente = Cliente.query.filter_by(equipo_id=equipo_id).first()
    if not cliente:
        return jsonify({'activo': False, 'mensaje': 'Equipo no registrado'})
    return jsonify({
        'activo': cliente.activo,
        'nombre': cliente.nombre,
        'mensaje': 'Licencia activa' if cliente.activo else 'Licencia suspendida por mora'
    })

# ─── ENDPOINTS DEL PANEL DE ADMINISTRACIÓN ──────────────────────────────────
@app.route('/admin/clientes', methods=['GET'])
def listar_clientes():
    if not verificar_secret(request):
        return jsonify({'error': 'No autorizado'}), 401
    clientes = Cliente.query.all()
    return jsonify([{
        'id': c.id, 'nombre': c.nombre, 'equipo_id': c.equipo_id,
        'activo': c.activo, 'notas': c.notas,
        'fecha_registro': c.fecha_registro.strftime('%Y-%m-%d')
    } for c in clientes])

@app.route('/admin/clientes', methods=['POST'])
def crear_cliente():
    if not verificar_secret(request):
        return jsonify({'error': 'No autorizado'}), 401
    data = request.json
    if Cliente.query.filter_by(equipo_id=data['equipo_id']).first():
        return jsonify({'error': 'Equipo ya registrado'}), 400
    c = Cliente(nombre=data['nombre'], equipo_id=data['equipo_id'],
                notas=data.get('notas', ''))
    db.session.add(c)
    db.session.commit()
    return jsonify({'mensaje': f'Cliente {c.nombre} registrado', 'id': c.id}), 201

@app.route('/admin/clientes/<int:cid>/suspender', methods=['POST'])
def suspender(cid):
    if not verificar_secret(request):
        return jsonify({'error': 'No autorizado'}), 401
    c = Cliente.query.get_or_404(cid)
    c.activo = False
    db.session.commit()
    return jsonify({'mensaje': f'{c.nombre} suspendido'})

@app.route('/admin/clientes/<int:cid>/activar', methods=['POST'])
def activar(cid):
    if not verificar_secret(request):
        return jsonify({'error': 'No autorizado'}), 401
    c = Cliente.query.get_or_404(cid)
    c.activo = True
    db.session.commit()
    return jsonify({'mensaje': f'{c.nombre} activado'})

@app.route('/admin/clientes/<int:cid>', methods=['DELETE'])
def eliminar(cid):
    if not verificar_secret(request):
        return jsonify({'error': 'No autorizado'}), 401
    c = Cliente.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    return jsonify({'mensaje': f'{c.nombre} eliminado'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
