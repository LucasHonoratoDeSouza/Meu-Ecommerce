from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import update
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import bcrypt


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = "secrete-key"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db?check_same_thread=False'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)

########### Classes ############

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    isSeller = db.Column(db.Boolean(), nullable=False, default=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    productName = db.Column(db.String(20), nullable=False)  
    productPrice = db.Column(db.String(60), nullable=False)  
    inventory = db.Column(db.Integer, nullable=False)  
    seller = db.Column(db.String(60), nullable=False)
    image_path = db.Column(db.String(200))

class Orders(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(60), nullable=False)  
    orderName = db.Column(db.String(20), nullable=False)  
    orderPrice = db.Column(db.String(60), nullable=False)  
    orderStatus = db.Column(db.String(20), nullable=False)  
    orderDate = db.Column(db.Date(), nullable=False)
    address = db.Column(db.String(20), nullable=False)  
    
############ Rotas ############
    
@app.route("/")
def home():
    username = session.get("username")
    products = Product.query.all()
    user = User.query.filter_by(username=username).first()  # Obtendo o objeto 'User'
    return render_template("home.html", username=username, products=products, user=user)

@app.route("/home/addproducts", methods=["GET", "POST"])
def products():
    if "username" in session:
        username = session["username"]
        user = User.query.filter_by(username=session["username"]).first()
        if user.isSeller:
            if request.method == "POST":
                productName = request.form["product_name"]
                productPrice = request.form["product_price"]
                inventory = request.form["product_inventory"]

                if 'product_image' not in request.files:
                    flash('No file part')
                    return redirect(request.url)

                file = request.files['product_image']

                if file.filename == '':
                    flash('No selected file')
                    return redirect(request.url)

                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(os.path.join(UPLOAD_FOLDER, filename))

                    filepath = filepath.replace('\\', '/')

                    new_product = Product(productName=productName, seller=username, productPrice=productPrice, inventory=inventory,  image_path=filepath)
                    db.session.add(new_product)
                    db.session.commit()
                    return redirect(url_for("home"))

            return render_template("add_product.html", username=username, user=user)
        else:
            return redirect(url_for("home"))
    else:
        return redirect(url_for("login"))

@app.route("/home/<int:productID>")
def view_product(productID):
    username = session.get("username")
    user = User.query.filter_by(username=username).first()
    product = db.session.get(Product, productID)
    return render_template("product.html", username=username, user=user, product=product)

@app.route('/static/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/home/buy/<int:productID>", methods=["GET", "POST"])
def buy(productID): 
    username = session.get("username")
    user = User.query.filter_by(username=username).first()
    product = db.session.get(Product, productID)
    if request.method == "POST":
        productName = product.productName
        productPrice = product.productPrice
        current_date = datetime.now()
        address = request.form["endereço"]
        new_order = Orders(Name=username, orderName=productName, orderPrice=productPrice, orderStatus="pendente", orderDate=current_date, address=address)
        product.inventory -= 1
        db.session.add(new_order)
        db.session.commit()
        return redirect(url_for("pedidos")) 
    return render_template("buy.html", username=username, user=user, product=product)

@app.route("/pedidos", methods=["POST", "GET"])
def pedidos(): 
    username = session.get("username")
    user = User.query.filter_by(username=username).first()
    if user.isSeller:
        orders = Orders.query.all()
    else:
        orders = Orders.query.filter_by(Name=username).all()  # Filtra as ordens pelo nome do usuário
    return render_template("pedidos.html", orders=orders, user=user)

@app.route("/edit/<int:productID>", methods=["GET", "POST"])
def edit(productID): 
    username = session["username"]
    user = User.query.filter_by(username=username).first()
    product = Product.query.get(productID)

    if request.method == "POST":
        product.productName = request.form["product_name"]
        product.productPrice = request.form["product_price"]
        product.inventory = request.form["product_inventory"]
        
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("edit.html", username=username, user=user, product=product)


@app.route("/pedido/<int:order_id>", methods=["GET", "POST"])
def order_details(order_id):
    order = Orders.query.get(order_id)
    username = session.get("username")
    user = User.query.filter_by(username=username).first()
    if request.method == "POST":
        new_status = request.form["new_status"]
        order.orderStatus = new_status
        db.session.commit()
        flash("Status da ordem atualizado com sucesso!")
        return redirect(url_for("order_details", order_id=order_id, user=user))

    return render_template("pedido.html", order=order, user=user)

    

@app.route("/delete/<int:productID>", methods=["GET", "POST"])
def delete(productID): 

    username = session["username"]
    user = User.query.filter_by(username=username).first()
    product = Product.query.get(productID)

    if user.isSeller and product.seller == username:
        db.session.delete(product)
        db.session.commit()

    return redirect(url_for("home"))


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            session["username"] = user.username
            return redirect(url_for("home"))
        return render_template("login.html", error="Credenciais inválidas")
    return render_template("login.html")

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template("register.html", error="Nome de usuário já em uso")
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        new_user = User(username=username, password=hashed_password.decode('utf-8'))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("home"))

########### __init__ ############

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)





































































#
