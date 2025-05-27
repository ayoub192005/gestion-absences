from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from io import BytesIO
import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
db = SQLAlchemy(app)

# MODELS

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))

class Absence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    date = db.Column(db.Date)
    type = db.Column(db.String(50))  # journée, demi-journée, congé
    employee = db.relationship('Employee', backref=db.backref('absences', lazy=True))

# ROUTES

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        passwd = request.form['password']
        if (uname == 'admin' and passwd == '1234') or (uname == 'mohamed' and passwd == '123'):
            session['user'] = uname
            return redirect(url_for('absences'))
        else:
            return render_template('login.html', error="Identifiants incorrects")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('login'))
    employees = Employee.query.all()
    return render_template('dashboard.html', employees=employees)

@app.route('/add_employee', methods=['POST'])
def add_employee():
    if 'user' in session and session['user'] == 'admin':
        name = request.form['name']
        if name:
            new_emp = Employee(name=name)
            db.session.add(new_emp)
            db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/absences')
def absences():
    if 'user' not in session:
        return redirect(url_for('login'))
    employees = Employee.query.all()
    absences = Absence.query.all()
    return render_template('absences.html', employees=employees, absences=absences)

@app.route('/add_absence', methods=['POST'])
def add_absence():
    if 'user' not in session:
        return redirect(url_for('login'))
    emp_id = request.form['employee_id']
    date = request.form['date']
    absence_type = request.form['type']
    absence = Absence(employee_id=emp_id, date=datetime.datetime.strptime(date, "%Y-%m-%d"), type=absence_type)
    db.session.add(absence)
    db.session.commit()
    return redirect(url_for('absences'))

@app.route('/edit_absence/<int:id>', methods=['POST'])
def edit_absence(id):
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('login'))
    absence = Absence.query.get_or_404(id)
    absence.date = datetime.datetime.strptime(request.form['date'], "%Y-%m-%d")
    absence.type = request.form['type']
    db.session.commit()
    return redirect(url_for('absences'))

@app.route('/delete_absence/<int:id>')
def delete_absence(id):
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('login'))
    absence = Absence.query.get_or_404(id)
    db.session.delete(absence)
    db.session.commit()
    return redirect(url_for('absences'))

@app.route('/export_excel')
def export_excel():
    if 'user' not in session:
        return redirect(url_for('login'))
    absences = Absence.query.all()
    data = [{
        'Employé': a.employee.name,
        'Date': a.date.strftime('%Y-%m-%d'),
        'Type': a.type
    } for a in absences]
    df = pd.DataFrame(data)
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Absences')
    writer.close()
    output.seek(0)
    return send_file(output, download_name="absences.xlsx", as_attachment=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
