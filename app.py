from flask import Flask, render_template, request, redirect, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

app = Flask(__name__)
app.secret_key = "pharmacy_management_secret_key"


def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="gaurav",
        database="pharmacy_db"
    )


def login_required():
    return "user_id" in session


@app.route("/")
def index():

    if not login_required():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM medicines")
    total_medicines = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM customers")
    total_customers = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM suppliers")
    total_suppliers = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM medicines
    """)
    total_stock = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM bills
        WHERE DATE(bill_date) = CURDATE()
    """)
    today_sales = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM purchases
        WHERE DATE(purchase_date) = CURDATE()
    """)
    today_purchases = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM bills
        WHERE DATE(bill_date) = CURDATE()
    """)
    today_bills = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM medicines
        WHERE quantity <= 10
    """)
    low_stock = cursor.fetchone()["total"]

    cursor.close()
    db.close()

    return render_template(
        "index.html",
        total_medicines=total_medicines,
        total_customers=total_customers,
        total_suppliers=total_suppliers,
        total_stock=total_stock,
        today_sales=today_sales,
        today_purchases=today_purchases,
        today_bills=today_bills,
        low_stock=low_stock
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE username = %s",
            (username,)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect("/")

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


@app.route("/create_users")
def create_users():

    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM users")

    admin_password = generate_password_hash("admin123")
    pharmacist_password = generate_password_hash("pharma123")

    cursor.execute("""
        INSERT INTO users
        (username, password, role)
        VALUES (%s, %s, %s)
    """, (
        "admin",
        admin_password,
        "Admin"
    ))

    cursor.execute("""
        INSERT INTO users
        (username, password, role)
        VALUES (%s, %s, %s)
    """, (
        "pharmacist",
        pharmacist_password,
        "Pharmacist"
    ))

    db.commit()

    cursor.close()
    db.close()

    return """
    <h2>Users created successfully.</h2>
    <p>Admin: admin / admin123</p>
    <p>Pharmacist: pharmacist / pharma123</p>
    <p><a href="/login">Go to Login</a></p>
    """


@app.route("/medicines")
def medicines():

    if not login_required():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM medicines
        ORDER BY medicine_id DESC
    """)

    medicines = cursor.fetchall()

    cursor.close()
    db.close()

    current_date = date.today()

    return render_template(
        "medicines.html",
        medicines=medicines,
        current_date=current_date
    )


@app.route("/add_medicine", methods=["GET", "POST"])
def add_medicine():

    if not login_required():
        return redirect("/login")

    if session.get("role") != "Admin":
        return "Access Denied. Admin only."

    if request.method == "POST":

        medicine_name = request.form["medicine_name"]
        category = request.form["category"]
        manufacturer = request.form["manufacturer"]
        batch_number = request.form["batch_number"]
        expiry_date = request.form["expiry_date"]
        price = request.form["price"]
        quantity = request.form["quantity"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO medicines
            (
                medicine_name,
                category,
                manufacturer,
                batch_number,
                expiry_date,
                price,
                quantity
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            medicine_name,
            category,
            manufacturer,
            batch_number,
            expiry_date,
            price,
            quantity
        ))

        db.commit()

        cursor.close()
        db.close()

        return redirect("/medicines")

    return render_template("add_medicine.html")


@app.route("/edit_medicine/<int:id>", methods=["GET", "POST"])
def edit_medicine(id):

    if not login_required():
        return redirect("/login")

    if session.get("role") != "Admin":
        return "Access Denied. Admin only."

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        medicine_name = request.form["medicine_name"]
        category = request.form["category"]
        manufacturer = request.form["manufacturer"]
        batch_number = request.form["batch_number"]
        expiry_date = request.form["expiry_date"]
        price = request.form["price"]
        quantity = request.form["quantity"]

        cursor.execute("""
            UPDATE medicines
            SET
                medicine_name = %s,
                category = %s,
                manufacturer = %s,
                batch_number = %s,
                expiry_date = %s,
                price = %s,
                quantity = %s
            WHERE medicine_id = %s
        """, (
            medicine_name,
            category,
            manufacturer,
            batch_number,
            expiry_date,
            price,
            quantity,
            id
        ))

        db.commit()

        cursor.close()
        db.close()

        return redirect("/medicines")

    cursor.execute("""
        SELECT *
        FROM medicines
        WHERE medicine_id = %s
    """, (id,))

    medicine = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "edit_medicine.html",
        medicine=medicine
    )


@app.route("/delete_medicine/<int:id>")
def delete_medicine(id):

    if not login_required():
        return redirect("/login")

    if session.get("role") != "Admin":
        return "Access Denied. Admin only."

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        DELETE FROM medicines
        WHERE medicine_id = %s
    """, (id,))

    db.commit()

    cursor.close()
    db.close()

    return redirect("/medicines")


@app.route("/customers")
def customers():

    if not login_required():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM customers
        ORDER BY customer_id DESC
    """)

    customers = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "customers.html",
        customers=customers
    )


@app.route("/add_customer", methods=["GET", "POST"])
def add_customer():

    if not login_required():
        return redirect("/login")

    if session.get("role") != "Admin":
        return "Access Denied. Admin only."

    if request.method == "POST":

        customer_name = request.form["customer_name"]
        phone = request.form["phone"]
        email = request.form["email"]
        address = request.form["address"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO customers
            (
                customer_name,
                phone,
                email,
                address
            )
            VALUES (%s, %s, %s, %s)
        """, (
            customer_name,
            phone,
            email,
            address
        ))

        db.commit()

        cursor.close()
        db.close()

        return redirect("/customers")

    return render_template("add_customer.html")


@app.route("/edit_customer/<int:id>", methods=["GET", "POST"])
def edit_customer(id):

    if not login_required():
        return redirect("/login")

    if session.get("role") != "Admin":
        return "Access Denied. Admin only."

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        customer_name = request.form["customer_name"]
        phone = request.form["phone"]
        email = request.form["email"]
        address = request.form["address"]

        cursor.execute("""
            UPDATE customers
            SET
                customer_name = %s,
                phone = %s,
                email = %s,
                address = %s
            WHERE customer_id = %s
        """, (
            customer_name,
            phone,
            email,
            address,
            id
        ))

        db.commit()

        cursor.close()
        db.close()

        return redirect("/customers")

    cursor.execute("""
        SELECT *
        FROM customers
        WHERE customer_id = %s
    """, (id,))

    customer = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "edit_customer.html",
        customer=customer
    )


@app.route("/delete_customer/<int:id>")
def delete_customer(id):

    if not login_required():
        return redirect("/login")

    if session.get("role") != "Admin":
        return "Access Denied. Admin only."

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        DELETE FROM customers
        WHERE customer_id = %s
    """, (id,))

    db.commit()

    cursor.close()
    db.close()

    return redirect("/customers")


@app.route("/suppliers")
def suppliers():

    if not login_required():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM suppliers
        ORDER BY supplier_id DESC
    """)

    suppliers = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "suppliers.html",
        suppliers=suppliers
    )


@app.route("/add_supplier", methods=["GET", "POST"])
def add_supplier():

    if not login_required():
        return redirect("/login")

    if session.get("role") != "Admin":
        return "Access Denied. Admin only."

    if request.method == "POST":

        supplier_name = request.form["supplier_name"]
        company_name = request.form["company_name"]
        phone = request.form["phone"]
        email = request.form["email"]
        address = request.form["address"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO suppliers
            (
                supplier_name,
                company_name,
                phone,
                email,
                address
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            supplier_name,
            company_name,
            phone,
            email,
            address
        ))

        db.commit()

        cursor.close()
        db.close()

        return redirect("/suppliers")

    return render_template("add_supplier.html")


@app.route("/edit_supplier/<int:id>", methods=["GET", "POST"])
def edit_supplier(id):

    if not login_required():
        return redirect("/login")

    if session.get("role") != "Admin":
        return "Access Denied. Admin only."

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        supplier_name = request.form["supplier_name"]
        company_name = request.form["company_name"]
        phone = request.form["phone"]
        email = request.form["email"]
        address = request.form["address"]

        cursor.execute("""
            UPDATE suppliers
            SET
                supplier_name = %s,
                company_name = %s,
                phone = %s,
                email = %s,
                address = %s
            WHERE supplier_id = %s
        """, (
            supplier_name,
            company_name,
            phone,
            email,
            address,
            id
        ))

        db.commit()

        cursor.close()
        db.close()

        return redirect("/suppliers")

    cursor.execute("""
        SELECT *
        FROM suppliers
        WHERE supplier_id = %s
    """, (id,))

    supplier = cursor.fetchone()

    cursor.close()
    db.close()

    return render_template(
        "edit_supplier.html",
        supplier=supplier
    )


@app.route("/delete_supplier/<int:id>")
def delete_supplier(id):

    if not login_required():
        return redirect("/login")

    if session.get("role") != "Admin":
        return "Access Denied. Admin only."

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        DELETE FROM suppliers
        WHERE supplier_id = %s
    """, (id,))

    db.commit()

    cursor.close()
    db.close()

    return redirect("/suppliers")


@app.route("/billing", methods=["GET", "POST"])
def billing():

    if not login_required():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        customer_id = request.form["customer_id"]

        medicine_ids = request.form.getlist(
            "medicine_id[]"
        )

        quantities = request.form.getlist(
            "quantity[]"
        )

        total_amount = 0
        items = []

        for i in range(len(medicine_ids)):

            medicine_id = medicine_ids[i]
            quantity = int(quantities[i])

            cursor.execute("""
                SELECT *
                FROM medicines
                WHERE medicine_id = %s
            """, (medicine_id,))

            medicine = cursor.fetchone()

            if medicine is None:
                continue

            if medicine["quantity"] < quantity:

                cursor.close()
                db.close()

                return (
                    "Insufficient stock for "
                    + medicine["medicine_name"]
                )

            price = float(medicine["price"])

            subtotal = price * quantity

            total_amount += subtotal

            items.append({
                "medicine_id": medicine_id,
                "quantity": quantity,
                "price": price,
                "subtotal": subtotal
            })

        cursor.execute("""
            INSERT INTO bills
            (
                customer_id,
                total_amount
            )
            VALUES (%s, %s)
        """, (
            customer_id,
            total_amount
        ))

        bill_id = cursor.lastrowid

        for item in items:

            cursor.execute("""
                INSERT INTO bill_items
                (
                    bill_id,
                    medicine_id,
                    quantity,
                    price,
                    subtotal
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                bill_id,
                item["medicine_id"],
                item["quantity"],
                item["price"],
                item["subtotal"]
            ))

            cursor.execute("""
                UPDATE medicines
                SET quantity = quantity - %s
                WHERE medicine_id = %s
            """, (
                item["quantity"],
                item["medicine_id"]
            ))

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            "/view_bill/" + str(bill_id)
        )

    cursor.execute("""
        SELECT *
        FROM customers
        ORDER BY customer_name
    """)

    customers = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM medicines
        WHERE quantity > 0
        ORDER BY medicine_name
    """)

    medicines = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "billing.html",
        customers=customers,
        medicines=medicines
    )


@app.route("/bill_history")
def bill_history():

    if not login_required():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            bills.bill_id,
            bills.bill_date,
            bills.total_amount,
            customers.customer_name
        FROM bills
        LEFT JOIN customers
        ON bills.customer_id = customers.customer_id
        ORDER BY bills.bill_id DESC
    """)

    bills = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "bill_history.html",
        bills=bills
    )


@app.route("/view_bill/<int:id>")
def view_bill(id):

    if not login_required():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            bills.*,
            customers.customer_name,
            customers.phone,
            customers.email,
            customers.address
        FROM bills
        LEFT JOIN customers
        ON bills.customer_id = customers.customer_id
        WHERE bills.bill_id = %s
    """, (id,))

    bill = cursor.fetchone()

    cursor.execute("""
        SELECT
            bill_items.*,
            medicines.medicine_name
        FROM bill_items
        JOIN medicines
        ON bill_items.medicine_id = medicines.medicine_id
        WHERE bill_items.bill_id = %s
    """, (id,))

    items = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "view_bill.html",
        bill=bill,
        items=items
    )


@app.route("/stock")
def stock():

    if not login_required():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM medicines
        ORDER BY quantity ASC
    """)

    medicines = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "stock.html",
        medicines=medicines,
        current_date=date.today()
    )


@app.route("/purchase", methods=["GET", "POST"])
def purchase():

    if not login_required():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        supplier_id = request.form["supplier_id"]

        medicine_ids = request.form.getlist(
            "medicine_id[]"
        )

        quantities = request.form.getlist(
            "quantity[]"
        )

        prices = request.form.getlist(
            "price[]"
        )

        total_amount = 0
        items = []

        for i in range(len(medicine_ids)):

            medicine_id = medicine_ids[i]
            quantity = int(quantities[i])
            price = float(prices[i])

            subtotal = quantity * price

            total_amount += subtotal

            items.append({
                "medicine_id": medicine_id,
                "quantity": quantity,
                "price": price,
                "subtotal": subtotal
            })

        cursor.execute("""
            INSERT INTO purchases
            (
                supplier_id,
                total_amount
            )
            VALUES (%s, %s)
        """, (
            supplier_id,
            total_amount
        ))

        purchase_id = cursor.lastrowid

        for item in items:

            cursor.execute("""
                INSERT INTO purchase_items
                (
                    purchase_id,
                    medicine_id,
                    quantity,
                    price,
                    subtotal
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                purchase_id,
                item["medicine_id"],
                item["quantity"],
                item["price"],
                item["subtotal"]
            ))

            cursor.execute("""
                UPDATE medicines
                SET quantity = quantity + %s
                WHERE medicine_id = %s
            """, (
                item["quantity"],
                item["medicine_id"]
            ))

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            "/view_purchase/" + str(purchase_id)
        )

    cursor.execute("""
        SELECT *
        FROM suppliers
        ORDER BY supplier_name
    """)

    suppliers = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM medicines
        ORDER BY medicine_name
    """)

    medicines = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "purchase.html",
        suppliers=suppliers,
        medicines=medicines
    )


@app.route("/purchase_history")
def purchase_history():

    if not login_required():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            purchases.purchase_id,
            purchases.purchase_date,
            purchases.total_amount,
            suppliers.supplier_name,
            suppliers.company_name
        FROM purchases
        LEFT JOIN suppliers
        ON purchases.supplier_id = suppliers.supplier_id
        ORDER BY purchases.purchase_id DESC
    """)

    purchases = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "purchase_history.html",
        purchases=purchases
    )


@app.route("/view_purchase/<int:id>")
def view_purchase(id):

    if not login_required():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            purchases.*,
            suppliers.supplier_name,
            suppliers.company_name,
            suppliers.phone,
            suppliers.email,
            suppliers.address
        FROM purchases
        LEFT JOIN suppliers
        ON purchases.supplier_id = suppliers.supplier_id
        WHERE purchases.purchase_id = %s
    """, (id,))

    purchase = cursor.fetchone()

    cursor.execute("""
        SELECT
            purchase_items.*,
            medicines.medicine_name
        FROM purchase_items
        JOIN medicines
        ON purchase_items.medicine_id = medicines.medicine_id
        WHERE purchase_items.purchase_id = %s
    """, (id,))

    items = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "view_purchase.html",
        purchase=purchase,
        items=items
    )


@app.route("/reports")
def reports():

    if not login_required():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM bills
        WHERE DATE(bill_date) = CURDATE()
    """)

    today_sales = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM purchases
        WHERE DATE(purchase_date) = CURDATE()
    """)

    today_purchases = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM bills
        WHERE YEAR(bill_date) = YEAR(CURDATE())
        AND MONTH(bill_date) = MONTH(CURDATE())
    """)

    monthly_sales = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM purchases
        WHERE YEAR(purchase_date) = YEAR(CURDATE())
        AND MONTH(purchase_date) = MONTH(CURDATE())
    """)

    monthly_purchases = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM bills
    """)

    overall_sales = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM purchases
    """)

    overall_purchases = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM medicines
    """)

    total_medicines = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM medicines
    """)

    total_stock = cursor.fetchone()["total"]

    cursor.close()
    db.close()

    return render_template(
        "reports.html",
        today_sales=today_sales,
        today_purchases=today_purchases,
        monthly_sales=monthly_sales,
        monthly_purchases=monthly_purchases,
        overall_sales=overall_sales,
        overall_purchases=overall_purchases,
        total_medicines=total_medicines,
        total_stock=total_stock
    )


if __name__ == "__main__":
    app.run(debug=True)