from requests import Session
from tkinter import *
import tkinter.messagebox as tm
from AnswerHandler import AnswerHandler
import traceback
import json
from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from parser_utils import Parser, NoQuestionFound, AAID_REGEX, FIND_DIGIT_REGEX


app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = '192.168.1.94'
app.config['MYSQL_USER'] = 'Bot'
app.config['MYSQL_PASSWORD'] = 'Bot'
app.config['MYSQL_DB'] = 'Botdata'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['SECRET_KEY'] = 'super secret key'
# init MYSQL
mysql = MySQL(app)


global log

log = False


@app.route('/')
def index():
    return render_template('home.html')




# Register Form Class
class Registerform(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
   
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')
    


# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    
    form = Registerform(request.form)
    
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        mysql.connection.commit()

        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)


# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        
        username = request.form['username']
        password_candidate = request.form['password']

        cur = mysql.connection.cursor()

        
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            
            data = cur.fetchone()
            password = data['password']
            adm = data['admin']

            
            if sha256_crypt.verify(password_candidate, password):
                
                session['logged_in'] = True
                session['username'] = username
                if adm == 1:
                    session['admin'] = True
                else:
                    session['admin'] = False
                    
                
                flash('You are now logged in', 'success')
                return redirect(url_for('index'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

#Check for admin
def is_admin(g):
    @wraps(g)
    def wrap(*args, **kwargs):
        if session['admin'] == True:
            return g(*args, **kwargs)
        else:
            flash('Not admin', 'danger')
            return redirect(url_for('index'))
    return wrap


# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))






#Page which loads and returns the responce from the interafce
@app.route('/DFMAnswerTool', methods=['GET', 'POST'])
#@is_logged_in
def DFMAnswerTool():
    global act, log
    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password']
        quest = request.form['quest']

        if '@' not in email:
            email += '@utcportsmouth.org'
        try:
            act = Interface(email, password)
            log = True
            tsl = 30
            res, err, feedback, resp = act.main_loop(quest, int(tsl), False, 'Test')#session['username'])
            out = feedback
            return render_template('output.html', msg='Completed Questions for Url', inf=out)
        except InvalidLoginDetails as e:
            log=False
            return render_template('DFMAnswerTool.html',error = ('Invalid login: '+ str(e)))
            
    return render_template('DFMAnswerTool.html')

#not used
@app.route('/DFMAnswerTool/Output', methods=['GET', 'POST'])
#@is_logged_in
def Output():
    global act, log
    if log==True:
                    
        return render_template('output.html')
    else:
        flash('Login in your DR Frost', 'danger')
        return redirect(url_for('DFMAnswerTool'))




@app.route('/about')
def about():
    
    return render_template('about.html')


@app.route('/dashboard', methods=['GET', 'POST'])
@is_logged_in
def dashboard():
    if request.method == 'POST':
        sys.exit()
    return render_template('dashboard.html')

    
class InvalidLoginDetails(Exception):
    pass

#Interface for each user
class Interface:
    
    def __init__(self, email, password):
        self.session = Session()
        self.test_login(email, password)
        self.handler = AnswerHandler(self.session)

    def main_loop(self, url, tsl, adm, email):
        
        print('Starting Solve for:\n', email)
        res=False
        while res==False:
            
            handler = AnswerHandler(self.session)
            res, err, feedback, resp = handler.answer_questions_V2(url,True, tsl, adm)

            print('Finished Solve for:\n', email)
            return res, err, feedback, resp 
        


    def test_login(self, email, password):
        login_url = 'https://www.drfrostmaths.com/process-login.php?url='
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                                 ' Chrome/71.0.3578.98 Safari/537.36'}
        data = {'login-email': email, 'login-password': password}
        self.session.post(login_url, headers=headers, data=data)
        try:
            """
            verifying user is authenticated by tests if user can load the times tables
            """
            res = self.session.get('https://www.drfrostmaths.com/homework/process-starttimestables.php')
            json.loads(res.text)
        except BaseException:
            raise InvalidLoginDetails(f'Email: {email}, Password: {"*" * len(password)}')
        
    @staticmethod
    def print_init():
        print_string = ''
        print(print_string)

    



if __name__ == '__main__':
    
    app.secret_key = 'super secret key'
    app.run( host='192.168.1.94', port=9000, debug=False)
    
