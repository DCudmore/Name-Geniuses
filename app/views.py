from flask import render_template, flash, redirect,url_for, g, request
from app import app,db,lm
from .forms import LoginForm,ForgotForm, PostForm,SuggestForm,NewPasswordForm,\
    EditForm,ContactForm,AdminEmailForm,RegHybridForm
from flask.ext.login import login_user, logout_user,\
    current_user, login_required
from datetime import datetime
from .models import User, Posting, Suggestion
from flask.ext.sqlalchemy import get_debug_queries
from config import DATABASE_QUERY_TIMEOUT, ADMINS
import stripe
from .token import generate_confirmation_token, confirm_token
from .emails import send_email, newemailsignup,sendbulk
from .decorators import check_confirmed, check_admin
from .domain import checkDomain, subscribe


@lm.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.before_request
def before_request():
    g.user = current_user   
    if g.user.is_authenticated:
        g.user.last_seen = datetime.utcnow()
        db.session.add(g.user)
        db.session.commit()    

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html',
                           title='Home',
                           defaultfooter=True,
                           heatmap=True,
                           home=True)
                           
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
@check_confirmed
def dashboard():
    user = g.user
    current_postings = Posting.query.filter_by(user_id=user.id).all()
    allpostings=Posting.query.all()
    current_suggestions=Suggestion.query.filter_by(suggester=user.id).all()
    counter=0
    for s in current_suggestions:
        counter+=1
    currentwins=user.wins
    winnings=user.totalwinnings
    notifications=user.emailnotes        
    return render_template('dashboard.html',
                           title='Dashboard',
                           user=user,
                           projects=current_postings,
                           suggestions=current_suggestions,
                           count=counter,
                           currentwins=currentwins,
                           winnings=winnings,
                           allpostings=allpostings,
                           notifications=notifications
                           )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('dashboard'))
    form=LoginForm()
    if form.validate_on_submit():
        username = form.email.data.lower()
        password = form.password.data
        user=User.query.filter_by(email=username).first()
        if user is None:
            flash("You haven't registered yet")
            return redirect(url_for('login'))            
        if user.is_correct_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash("Incorrect username or password")
            return redirect(url_for('login'))                        
    return render_template('login.html', 
                           title='Sign In',
                           form=form,
                           canonical="login")
                           
@app.route('/forgotpassword', methods=['GET', 'POST'])
def forgotpassword():
    form=ForgotForm()     
    if form.validate_on_submit():
        email = form.email.data
        user=User.query.filter_by(email=email).first()
        if user is None:
            flash("There is no user with this email address")
            return render_template('forgotpassword.html', 
                       title='Forgot Password',
                       form=form)
        else:           
            token = generate_confirmation_token(user.email)
            flash('An email has been sent to your email address!')
            reset_url = url_for('newpassword', token=token, _external=True)
            html = render_template('passwordemail.html', reset_url=reset_url)
            subject = "Your password resetting instructions"
            send_email(user.email, subject, html)             
    return render_template('forgotpassword.html', 
                           title='Forgot Password',
                           form=form,
                           canonical="forgotpassword")         

@app.route('/newpassword/<token>', methods=['GET', 'POST'])
def newpassword(token):
    try:
        email = confirm_token(token)
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')
    user = User.query.filter_by(email=email).first()
    form=NewPasswordForm()     
    if form.validate_on_submit():
        user.password = form.password.data
        db.session.commit()
        flash("Your password has been changed successfully!")
        return redirect(url_for('login'))                        
        
    return render_template('newpassword.html', 
                           title='Choose your new password',
                           form=form) 
                           
@app.route('/register', methods=['GET', 'POST'])
def register():
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('dashboard'))
    form=RegHybridForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        pw= form.password.data
        user=User.query.filter_by(email=email).first()
        title = form.title.data
        description= form.description.data
        anyelse=form.Anything_else.data
        project_type="Essential"
        project_prize=float(form.project_prize.data)
        time=datetime.utcnow()
        timeday=time.date()
        filteraddon=form.addon_filter.data
        validation=form.addon_validation.data
        if user is None:
            user=User(email=email,password=pw,jobposter=True,paypalemail=email)
            db.session.add(user)
            db.session.commit()
            project=Posting(title=title, anything_else=anyelse, description=description, creator=user, timestamp=time, timestamp_day=timeday, validation_addon=validation, filter_addon=filteraddon, project_type=project_type, project_prize=project_prize)
            db.session.add(project)
            db.session.commit()
            
            token = generate_confirmation_token(user.email)
            confirm_url = url_for('confirm_email', token=token, _external=True)
            html = render_template('activate.html', confirm_url=confirm_url)
            subject = "Please confirm your email"
            send_email(user.email, subject, html)                        
            
            login_user(user, True)
            newemailsignup(email=email)
            flash('Your project has been created!')
            return redirect(url_for('unconfirmed'))            
        if user.is_correct_password(pw):
            login_user(user)
            project=Posting(title=title, anything_else=anyelse, description=description, creator=user, timestamp=time, timestamp_day=timeday, validation_addon=validation, filter_addon=filteraddon, project_type=project_type, project_prize=project_prize)
            db.session.add(project)
            db.session.commit()
            return redirect(url_for('dashboard'))        
        else:
            flash("Username exists, but not with that password")
            return redirect(url_for('dashboard'))        

    return render_template('register.html', 
                           title='Register',
                           form=form,
                           heatmap=True)

@app.route('/confirm/<token>')
@login_required
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')
    user = User.query.filter_by(email=email).first()
    if user.confirmed is True:
        flash('Account already confirmed. Please login.', 'success')
    else:
        user.confirmed = True
        user.timestamp = datetime.utcnow()
        db.session.commit()
        if user.jobposter==True:
            html = render_template('welcome.html')
            subject = "Welcome to Name Geniuses - Here's how to get started"
            send_email(user.email, subject, html)   
        else:
            html = render_template('welcomesugg.html')
            subject = "Welcome to Name Geniuses - Here's how to get started"
            send_email(user.email, subject, html)   
            return redirect(url_for('dashboard'))  
        flash('You have confirmed your account. Thanks!', 'success')
        
    return redirect(url_for('dashboard'))

@app.route('/resend')
@login_required
def resend_confirmation():
    token = generate_confirmation_token(current_user.email)
    confirm_url = url_for('confirm_email', token=token, _external=True)
    html = render_template('activate.html', confirm_url=confirm_url)
    subject = "Please confirm your email"
    send_email(current_user.email, subject, html)
    flash('A new confirmation email has been sent.', 'success')
    return redirect(url_for('unconfirmed'))
    


@app.route('/newproject', methods=['GET', 'POST'])
@login_required
@check_confirmed
def newproject():
    form=PostForm()
    if form.validate_on_submit():
        title = form.title.data
        description= form.description.data
        anyelse=form.Anything_else.data
        project_prize=float(form.project_prize.data)
        time=datetime.utcnow()
        timeday=time.date()
        project_type="Essential"
        filteraddon=form.addon_filter.data
        validation=form.addon_validation.data
        project=Posting(title=title, anything_else=anyelse, description=description, creator=g.user, timestamp=time, timestamp_day=timeday, validation_addon=validation, filter_addon=filteraddon, project_type=project_type, project_prize=project_prize)
        db.session.add(project)
        db.session.commit()     
        return redirect(url_for('dashboard'))
    else:
        flash_errors(form)
    return render_template('newproject.html', 
                           title='Create a new project',
                           form=form)
 
def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ))
                                 
@app.route('/project/<pnumber>')
def projectpage(pnumber):
    user=g.user
    projectdata = Posting.query.filter_by(id=pnumber).first()
    suggestdata= Suggestion.query.filter_by(posting_id=pnumber).all()
    winstatus=projectdata.winner
    if winstatus:
        winnerchosen=True
    else:
        winnerchosen=False
    return render_template('projectpage.html',
                           user=user,
                           pdata=projectdata,
                           suggestdata=suggestdata,
                           winnerchosen=winnerchosen,
                           winstatus=winstatus,
                           title="Project details")
                           

@app.route('/project/<pnumber>/admin')
@login_required
@check_admin
def projectpageadmin(pnumber):
    user=g.user
    projectdata = Posting.query.filter_by(id=pnumber).first()
    suggestdata= Suggestion.query.filter_by(posting_id=pnumber).all()
    winstatus=projectdata.winner
    if winstatus:
        winnerchosen=True
    else:
        winnerchosen=False
    return render_template('projectpageadmin.html',
                           user=user,
                           pdata=projectdata,
                           suggestdata=suggestdata,
                           winnerchosen=winnerchosen,
                           winstatus=winstatus,
                           title="Project details")

@app.route('/postings')
def postings():
    allprojects = Posting.query.filter_by(status="Live").order_by("timestamp desc").all()
    closedprojects = Posting.query.filter_by(status="Closed").all()    
    return render_template('allprojects.html',
                           allprojects=allprojects,
                           closedprojects=closedprojects,
                           title="All projects",
                           canonical="postings")

@app.route('/pickwinner/<pnumber>/<suggest>/<suggnumber>')
@login_required
@check_confirmed
def pickwinner(pnumber,suggest,suggnumber):
    user=g.user
    #get the project entry
    project = Posting.query.filter_by(id=pnumber).first()
    if project.winner:
        flash("You've already picked a winner")
        return redirect(url_for('projectpage', pnumber=pnumber))
    #checks if current user (the project poster) is equal to the project poster; just to ensure no one else is able to pick a winner
    if user.id==project.user_id or user.admin==True:
        winner=Suggestion.query.filter_by(id=suggest).first()
        winner.winstatus=True
        project.status="Closed"
        if suggnumber=="1":
            project.winner=winner.Suggest1
        if suggnumber=="2":
            project.winner=winner.Suggest2
        if suggnumber=="3":
            project.winner=winner.Suggest3
        if suggnumber=="4":
            project.winner=winner.Suggest4
        if suggnumber=="5":
            project.winner=winner.Suggest5
        #add the win to the suggester
        winningsuggester=User.query.filter_by(id=winner.suggester).first()
        winningsuggester.wins+=1
        if project.project_type== "Essential":
            won=project.project_prize*0.8
            winningsuggester.totalwinnings+=won
            winningsuggester.paydue+=won
        else:
            won=(project.project_prize-40)*0.8  
            winningsuggester.totalwinnings+=won
            winningsuggester.paydue+=won
        db.session.commit()
    return redirect(url_for('dashboard'))



@app.route('/suggest/<pnumber>', methods=['GET', 'POST'])
@login_required
@check_confirmed
def suggest(pnumber):
    user=g.user
    form=SuggestForm()
    projectdata = Posting.query.filter_by(id=pnumber).first()
    if form.validate_on_submit():
        prevsugg=Suggestion.query.filter_by(suggester=user.id).filter_by(posting_id=pnumber).first()
        try:
            if prevsugg.Suggest5:
                flash("You've already made 5 suggestions for this project (the maximum allowed), please pick a different one")
                return redirect(url_for('dashboard'))
        except:
            pass
        Suggest1 = form.Suggest1.data
        Suggest2 = form.Suggest2.data
        Suggest3 = form.Suggest3.data
        Suggest4 = form.Suggest4.data
        Suggest5 = form.Suggest5.data
        badnames=[]
        count=0
        if Suggest1:        
            count+=1
            if not checkDomain(Suggest1):
                badnames.append(Suggest1)
        if Suggest2: 
            count+=1            
            if not checkDomain(Suggest2):
                badnames.append(Suggest2)
        if Suggest3:     
            count+=1
            if not checkDomain(Suggest3):
                badnames.append(Suggest3)
        if Suggest4:     
            count+=1
            if not checkDomain(Suggest4):
                badnames.append(Suggest4)
        if Suggest5:     
            count+=1
            if not checkDomain(Suggest5):
                badnames.append(Suggest5)
        if badnames:
            return render_template('suggestion.html',
                           form=form,
                           badnames=badnames,
                           pdata=projectdata,
                           title="Make a suggestion")       
        try:
            if prevsugg.Suggest1:
                secondcount=0
                list1=[prevsugg.Suggest1,prevsugg.Suggest2,prevsugg.Suggest3,prevsugg.Suggest4,prevsugg.Suggest5]
                for l in range(4,-1,-1):
                    if len(list1[l])<3:
                        del list1[l]
                list2=[Suggest1, Suggest2,Suggest3, Suggest4, Suggest5]
                list3=list1+list2
                for domain in list3:
                    if len(domain)>2:
                        secondcount+=1
                fulllist=secondcount-len(list1)
                prevsugg.Suggest1=list3[0]
                prevsugg.Suggest2=list3[1]
                prevsugg.Suggest3=list3[2]
                prevsugg.Suggest4=list3[3]
                prevsugg.Suggest5=list3[4]
                projectdata.number_of_entries+=fulllist
                db.session.commit()
        except:
            time=datetime.utcnow()
            timeday=time.date()
            Suggestions=Suggestion(Suggest1=Suggest1, Suggest2=Suggest2,Suggest3=Suggest3,Suggest4=Suggest4,Suggest5=Suggest5, poster=projectdata, suggester=user.id, timestamp=time, timestamp_day=timeday)
            projectdata.number_of_entries+=count            
            db.session.add(Suggestions)
            db.session.commit()
        flash('Your suggestions have been submitted!')
        return redirect(url_for('projectpage',pnumber=projectdata.id))
    return render_template('suggestion.html',
                           form=form,
                           pdata=projectdata,
                           title="Make a suggestion")

@app.route('/becomesuggester', methods=['GET', 'POST'])
def suggester():
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('becomesuggester.html', 
                           title='Become a suggester',
                           canonical="becomesuggester")


@app.route('/registersuggester', methods=['GET', 'POST'])
def registersuggester():
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('dashboard'))
    form=LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        pw= form.password.data
        user=User.query.filter_by(email=email).first()
        if user is None:
            user=User(email=email,password=pw,suggester=True,paypalemail=email)
            db.session.add(user)
            db.session.commit()
            subscribe(email=email)

            token = generate_confirmation_token(user.email)
            flash('Your account has been created!')
            confirm_url = url_for('confirm_email', token=token, _external=True)
            html = render_template('activate.html', confirm_url=confirm_url)
            subject = "Please confirm your email"
            send_email(user.email, subject, html)                           
        
            login_user(user, True)
            return redirect(url_for('dashboard'))            
        if user.is_correct_password(pw):
            login_user(user)
            return redirect(url_for('dashboard'))        
        else:
            flash("Username exists, but not with that password")
            return redirect(url_for('dashboard'))   
    return render_template('registersuggester.html', 
                           title='Register as a suggester',
                           form=form)

@app.route('/charge/<projectid>/<amount>', methods=['POST'])
@login_required
@check_confirmed
def charge(projectid,amount):
    # Amount in cents
    realamount=int(float(amount)*100)
    user=g.user
    customer = stripe.Customer.create(
        email=user.email,
        card=request.form['stripeToken']
    )

    charge = stripe.Charge.create(
        customer=customer.id,
        amount=realamount,
        currency='usd',
        description='Charge for name suggestions'
    )
    Projectrecord=Posting.query.filter_by(id=projectid).first()
    Projectrecord.status="Live"
    db.session.commit()    
    flash("Payment successful, your project is live!")
    
    html = render_template('expectations.html')
    subject = "Your Name Geniuses posting - what to expect"
    send_email(user.email, subject, html)
    
    return redirect(url_for('dashboard'))  

@app.route('/editprofile', methods=['GET', 'POST'])
@login_required
def editprofile():
    form=EditForm()
    user=g.user
    if form.validate_on_submit():
        email = form.paypalemail.data
        user.paypalemail=email
        db.session.commit()
        return redirect(url_for('dashboard'))
  
    return render_template('editprofile.html', 
                           title='Edit Profile',
                           form=form)
                                                      
@app.route('/payment/<ptype>/<pid>', methods=['GET', 'POST'])
def payment(pid, ptype):
    key=stripe_keys['publishable_key']
    project=Posting.query.filter_by(id=pid).first()    
    amount=project.project_prize
    if project.filter_addon:
        amount+=40
    if project.validation_addon:
        amount+=100
    centsamount=amount*100
    return render_template('payment.html', amount=amount, centsamount=centsamount,key=key, projectid=pid, title="Payment")

@app.route('/pricing')
def pricing():
    return render_template('pricing.html', 
                           title="Pricing",
                           heatmap=True,
                           canonical="pricing")

@app.route('/examples')
def examples():
    return render_template('examples.html', 
                           title="Examples of Winning Domain Names",
                           canonical="examples")

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form=ContactForm()
    if form.validate_on_submit():
        email = form.email.data
        name= form.name.data
        message=form.message.data
        html=render_template('contactmessage.html', name=name, email=email, message=message)
        send_email(to=ADMINS[0], subject="Name Geniuses Contact", template=html)   
        flash("Your message has been sent! I'll get back to you as soon as I can.")
    return render_template('contact.html', 
                           title="Contact", 
                           form=form,
                           canonical="contact")

@app.route('/adminemails', methods=['GET', 'POST'])
@login_required
@check_admin
def adminemails():
    form=AdminEmailForm()
    if form.validate_on_submit():
        subject = form.subject.data
        message=form.message.data
        lister=User.query.filter_by(suggester=True).filter_by(emailnotes=True).all()
        sendbulk(message=message, subject=subject, users=lister)
        #subject = form.subject.data
        #message=form.message.data
        #lister=User.query.filter_by(suggester=True).filter_by(emailnotes=True).all()
        #sendbulk(message=message, subject=subject, users=lister)
    return render_template('adminemails.html', 
                           title="Admin email panel",
                           form=form)

@app.route('/adminpay', methods=['GET', 'POST'])
@login_required
@check_admin
def adminpay():
    winners=User.query.filter(User.paydue>0).all()
    return render_template('adminpay.html', 
                           title="Admin pay page",
                           winners=winners)
                           
@app.route('/adminprojects')
@login_required
@check_admin
def adminprojects():
    projects = Posting.query.order_by("timestamp desc").all()

    return render_template('adminprojects.html', 
                           title="Admin project page",
                           projects=projects)

@app.route('/followup/<pid>')
@login_required
@check_admin
def followup(pid):    
    projectfollowup = Posting.query.filter_by(id=pid).first()
    poster=projectfollowup.user_id
    
    posterinfo=User.query.filter_by(id=poster).first()
    email=posterinfo.email
    html=render_template('followupemail.html')
    send_email(to=email, subject="Update on your Name Geniuses posting", template=html)    
    
    projects = Posting.query.order_by("timestamp desc").all()

    return render_template('adminprojects.html', 
                           title="Admin project page",
                           projects=projects)

@app.route('/adminusers')
@login_required
@check_admin
def adminusers():
    users=User.query.all()
    return render_template('adminusers.html', 
                           title="All users",
                           users=users)

@app.route('/admin')
@login_required
@check_admin
def admin():
    return render_template('admin.html', 
                           title="Adminpanel")     
              
@app.route('/paid/<user>', methods=['GET', 'POST'])
@login_required
@check_admin
def paid(user):
    u=User.query.filter_by(id=user).first()
    u.totalpaid=u.totalwinnings
    u.paydue=0
    db.session.commit()    
    winners=User.query.filter(User.paydue>0).all()
    return render_template('adminpay.html', 
                           title="Admin pay page",
                           winners=winners)                           


#functions
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')
    
@app.route('/turnoffnotifications')
@login_required
def turnoffnotifications():
    user=g.user
    user.emailnotes=False
    db.session.commit()  
    return redirect(url_for('dashboard'))

@app.route('/turnonnotifications')
@login_required
def turnonnotifications():
    user=g.user
    user.emailnotes=True
    db.session.commit()  
    return redirect(url_for('dashboard'))

@app.route('/unconfirmed')
@login_required
def unconfirmed():
    if current_user.confirmed is True:
        return redirect(url_for('index'))
    return render_template('unconfirmed.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    send_email(to=ADMINS[0], subject="500 error", template="There's a 500 error")
    return render_template('500.html'), 500
        
@app.after_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= DATABASE_QUERY_TIMEOUT:
            app.logger.warning("SLOW QUERY: %s\nParameters: %s\nDuration: %fs\nContext: %s\n" % (query.statement, query.parameters, query.duration, query.context))
    return response

@app.route('/sitemap')
def sitemap():
    return render_template('sitemap.xml')

