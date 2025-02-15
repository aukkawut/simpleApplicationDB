from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
db = SQLAlchemy(app)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.String(50), unique=True, nullable=False)
    national_id = db.Column(db.String(50), unique=True, nullable=False)
    initial = db.Column(db.String(10))
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(50))
    date_of_birth = db.Column(db.Date, nullable=False)
    previous_school = db.Column(db.String(200), nullable=False)
    province = db.Column(db.String(100), nullable=False)
    register_date = db.Column(db.Date, nullable=False)
    student_type = db.Column(db.String(20), nullable=False)
    gpax = db.Column(db.Float, nullable=False)
    exam_room = db.Column(db.String(50), nullable=False)
    exam_position = db.Column(db.String(50), nullable=False)
    program = db.Column(db.String(100), nullable=False)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search_page')
def search_page():
    programs = db.session.query(Student.program.distinct()).all()
    provinces = db.session.query(Student.province.distinct()).all()
    student_types = ['day', 'boarding']
    return render_template('search.html', 
                         programs=[p[0] for p in programs],
                         provinces=[p[0] for p in provinces],
                         student_types=student_types)

@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = request.form
        student = Student(
            application_id=data['application_id'],
            national_id=data['national_id'],
            initial=data['initial'],
            name=data['name'],
            surname=data['surname'],
            nickname=data['nickname'],
            date_of_birth=datetime.strptime(data['date_of_birth'], '%Y-%m-%d'),
            previous_school=data['previous_school'],
            province=data['province'],
            register_date=datetime.strptime(data['register_date'], '%Y-%m-%d'),
            student_type=data['student_type'],
            gpax=float(data['gpax']),
            exam_room=data['exam_room'],
            exam_position=data['exam_position'],
            program=data['program']
        )
        db.session.add(student)
        db.session.commit()
        return jsonify({'message': 'Success'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/search')
def search():
    query = request.args.get('q', '')
    program = request.args.get('program', '')
    province = request.args.get('province', '')
    student_type = request.args.get('student_type', '')
    min_gpax = request.args.get('min_gpax', '')
    max_gpax = request.args.get('max_gpax', '')
    sort_by = request.args.get('sort_by', 'application_id')
    sort_order = request.args.get('sort_order', 'asc')
    group_by = request.args.get('group_by', '')
    students_query = Student.query
    if query:
        students_query = students_query.filter(
            db.or_(
                Student.application_id.contains(query),
                Student.name.contains(query),
                Student.surname.contains(query),
                Student.national_id.contains(query),
                Student.previous_school.contains(query)
            )
        )
    
    if program:
        students_query = students_query.filter(Student.program == program)
    if province:
        students_query = students_query.filter(Student.province == province)
    if student_type:
        students_query = students_query.filter(Student.student_type == student_type)
    if min_gpax:
        students_query = students_query.filter(Student.gpax >= float(min_gpax))
    if max_gpax:
        students_query = students_query.filter(Student.gpax <= float(max_gpax))
    if sort_order == 'asc':
        students_query = students_query.order_by(getattr(Student, sort_by).asc())
    else:
        students_query = students_query.order_by(getattr(Student, sort_by).desc())
    students = students_query.all()
    results = [{
        'application_id': s.application_id,
        'national_id': s.national_id,
        'initial': s.initial,
        'name': s.name,
        'surname': s.surname,
        'nickname': s.nickname,
        'date_of_birth': s.date_of_birth.strftime('%Y-%m-%d'),
        'previous_school': s.previous_school,
        'province': s.province,
        'register_date': s.register_date.strftime('%Y-%m-%d'),
        'student_type': s.student_type,
        'gpax': s.gpax,
        'exam_room': s.exam_room,
        'exam_position': s.exam_position,
        'program': s.program
    } for s in students]
    if group_by and group_by in results[0].keys():
        grouped_results = {}
        for r in results:
            key = r[group_by]
            if key not in grouped_results:
                grouped_results[key] = []
            grouped_results[key].append(r)
        results = grouped_results

    return jsonify(results)

@app.route('/export_excel')
def export_excel():
    students = Student.query.all()
    data = [{
        'Application ID': s.application_id,
        'National ID': s.national_id,
        'Initial': s.initial,
        'Name': s.name,
        'Surname': s.surname,
        'Nickname': s.nickname,
        'Date of Birth': s.date_of_birth,
        'Previous School': s.previous_school,
        'Province': s.province,
        'Register Date': s.register_date,
        'Student Type': s.student_type,
        'GPAX': s.gpax,
        'Exam Room': s.exam_room,
        'Exam Position': s.exam_position,
        'Program': s.program
    } for s in students]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Students', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Students']
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1
        })
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        for i, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
            worksheet.set_column(i, i, max_length)

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='student_applications.xlsx'
    )

if __name__ == '__main__':
    app.run(debug=True)