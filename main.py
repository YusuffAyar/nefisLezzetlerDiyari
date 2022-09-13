from flask import Flask, render_template, flash, redirect, url_for, session, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapınız.", "danger")
            return redirect(url_for("login"))
    return decorated_function


class RegisterForm(Form):

    name = StringField("İsim ve Soyisim", validators=[validators.Length(min=5, max=25)])
    email = StringField("E-Mail Adresi", validators=[validators.Email(message="Lütfen Geçerli Bir E-Mail Adresi Giriniz")])
    username = StringField("Kullanıcı Adı", validators=[validators.Length(min=5, max=25)])
    password = PasswordField("Parola", validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyiniz"),
        validators.EqualTo(fieldname="confirm", message="Parolanız uyuşmuyor")
    ])
    confirm = PasswordField("Parola Doğrula")


class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")


app = Flask(__name__)
app.secret_key = "nefislezzetlerdiyari"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "nefislezzetlerdiyari"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/meals")
def meals():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From meals"
    result = cursor.execute(sorgu)
    if result > 0:
        meals = cursor.fetchall()
        return render_template("meals.html", meals=meals)
    else:
        return render_template("meals.html")


@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From meals where author = %s"
    result = cursor.execute(sorgu, (session["username"],))
    if result > 0:
        meals = cursor.fetchall()
        return render_template("dashboard.html", meals=meals)
    else:
        return render_template("dashboard.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(form.password.data)
        cursor = mysql.connection.cursor()
        sorgu = "Insert into users(name, email, username, password) VALUES(%s, %s, %s, %s)"
        cursor.execute(sorgu, (name, email, username, password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarılı bir şekilde kaydoldunuz.", "success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        sorgu = "Select * From users where username = %s"
        result = cursor.execute(sorgu, (username,))

        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered, real_password):
                flash("Başarıyla Giriş Yaptınız...", "success")

                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("Parolanızı yanlış girdiniz...", "danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor...", "danger")
            return redirect(url_for("login"))
    return render_template("login.html", form=form)


@app.route("/meal/<string:id>")
def meal(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * from meals where id = %s"
    result = cursor.execute(sorgu, (id,))
    if result > 0:
        meal = cursor.fetchone()
        return render_template("meal.html", meal=meal)
    else:
        return render_template("meal.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/addmeals", methods=["GET", "POST"])
def addmeals():
    form = MealForm(request.form)
    if request.method == "POST" and form.validate():
        meal_name = form.meal_name.data
        content = form.content.data
        cursor = mysql.connection.cursor()
        sorgu = "Insert into meals(meal_name, author, content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu, (meal_name, session["username"], content))
        mysql.connection.commit()
        cursor.close()
        flash("Yemek Başarıyla Eklendi", "success")
        return redirect(url_for("dashboard"))

    return render_template("addmeals.html", form=form)


@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * from meals where author = %s and id = %s"
    result = cursor.execute(sorgu, (session["username"], id))
    if result > 0:
        sorgu2 = "Delete from meals where id = %s"
        cursor.execute(sorgu2, (id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir yemek tarifi yok veya bu işleme yetkiniz yok...", "danger")
        return redirect(url_for("index"))


@app.route("/edit/<string:id>", methods=["GET", "POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "Select * from meals where id = %s and author = %s"
        result = cursor.execute(sorgu, (id, session["username"]))
        if result == 0:
            flash("Böyle bir yemek tarifi yok veya bu işleme yetkiniz yok...", "danger")
            return redirect(url_for("index"))
        else:
            meal = cursor.fetchone()
            form = MealForm()
            form.meal_name.data = meal["meal_name"]
            form.content.data = meal["content"]
            return render_template("update.html", form=form)
    else:
        form = MealForm(request.form)
        newmeal_name = form.meal_name.data
        newcontent = form.content.data
        sorgu2 = "Update meals Set meal_name = %s, content = %s where id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2, (newmeal_name, newcontent, id))
        mysql.connection.commit()
        flash("Yemek tarifi başarıyla güncellendi...", "success")
        return redirect(url_for("dashboard"))
        pass


class MealForm(Form):
    meal_name = StringField("Yemek Adı", validators=[validators.length(min=5, max=100)])
    content = TextAreaField("Yemek İçeriği", validators=[validators.Length(min=10)])


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sorgu = "Select * from meals where meal_name like '%" + keyword + "%'"
        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aranan kelimeye uygun yemek tarifi bulunamadı...", "warning")
            return redirect(url_for("meals"))
        else:
            meals = cursor.fetchall()
            return render_template("meals.html", meals=meals)


if __name__ == '__main__':
    app.debug = True
    app.run(host="localhost", port=1000)
