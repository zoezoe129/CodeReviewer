import argparse
import json
import os
import re
import random
import time
import smtplib
import uuid
import datetime
import imaplib
import email
import logging
from logging.handlers import RotatingFileHandler

# -------------------------------------------
#
# Commit class to contain commit related info
#
# -------------------------------------------
class Commit:
    def __init__(self, Id, Author, Date):
        self.Id = Id;
        self.Author = Author;
        self.Date = Date;

# -------------------------------------------
#
# Utility to read email inbox
#
# -------------------------------------------
def read_email(num_days):
    try:
        email_info = []
        email_server = imaplib.IMAP4_SSL(SERVER)
        email_server.login(FROM_EMAIL,FROM_PWD)
        email_server.select('inbox')
 
        email_date = datetime.date.today() - datetime.timedelta(days=num_days)
        formatted_date = email_date.strftime('%d-%b-%Y')
 
        typ, data = email_server.search(None, '(SINCE "' + formatted_date + '")')
        ids = data[0]
 
        id_list = ids.split()
 
        first_email_id = int(id_list[0])
        last_email_id = int(id_list[-1])
 
        for i in range(last_email_id,first_email_id, -1):
            typ, data = email_server.fetch(i, '(RFC822)' )
 
            for response_part in data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_string(response_part[1])
                    email_info.append({'From':msg['from'],'Subject':msg['subject'].replace("\r\n","")})
 
    except Exception, e:
        print str(e)
 
    return email_info

# ----------------------------------------
#
# Utility to save code review request info
#
# ----------------------------------------
def save_review_info(reviewer, subject):
    info = {'reviewer':reviewer,'subject':subject,'id':str(uuid.uuid4()),'sendDate':str(datetime.date.today())}
 
    with open('reviewer.json','r') as infile:
        review_data = json.load(infile)
 
    review_data.append(info)
 
    with open('reviewer.json','w') as outfile:
        json.dump(review_data,outfile)

# -----------------------------------------
#
# Method to select random reviewer
#
# -----------------------------------------
 def select_reviewer(author, group):
    if author in group:
        group.remove(author)
    reviewer = random.choice(group)
    return reviewer

# -----------------------------------------
#
# Utility to format review request
#
# -----------------------------------------
def format_review_commit(commit):
    review_req = ""
    review_req += "URL:     " + project_url + '/commit/' +  commit.Id + "\n"
    review_req += "Commit:  " + commit.Id + "\n"
    review_req += "Author:  " + commit.Author + "\n"
    review_req += "Date:    " + commit.Date + "\n"
    return review_req

# ------------------------------------------
#
# Method to Schedule the code review request
#
# ------------------------------------------
def schedule_review_request(commits):
    date = time.strftime("%Y-%m-%d")
     
    for commit in commits:
        reviewer = select_reviewer(commit.Author, project_members)
        subject = date + " Code Review [commit:" + commit.Id + "]"
        body = "Hello '" + reviewer + "', you have been selected to review the code for commit\n"
        body += "done by '" + commit.Author + "'.\n"
        body += "\n"
         
        body += format_review_commit(commit)
        print body
        save_review_info(reviewer, subject)
        send_email(reviewer,subject,body)
        
# ----------------------------------
#
# Utility to execute system commands
#
# ----------------------------------
def execute_cmd(cmd):
    print "***** Executing command '"+ cmd + "'"
    response = os.popen(cmd).read()
    return response

# ----------------------------------
#
# Process the git log 
#
# ----------------------------------  
def process_commits():
    cmd = "cd " + project + "; git log --all --since=" + str(no_days) + ".day --name-status"
    response = execute_cmd(cmd)
    commitId = ''
    author = ''
    date = ''
    commits = []

    for line in response.splitlines():
        if line.startswith('commit '):       
            if commitId <> "":
                commits.append(Commit(commitId, author, date))
            author = ''
            date = ''
            commitId = line[7:]
           # print  line[7:]
        if line.startswith('Author:'):
            if(re.search('\<(.*?)\>',line)):
               # print re.search('\<(.*?)\>',line).group(1)
               author=re.search('\<(.*?)\>',line).group(1)
        if line.startswith('Date:'):
            #print line[5:]
            date=line[5:]
    if commitId <> "":
        commits.append(Commit(commitId, author, date))
    
    return commits

# -----------------------------------------
#
# Utility to send email
#
# -----------------------------------------
def send_email(to, subject, body):
    header  = "From: " + FROM_EMAIL + "\n"
    header += "To: " + to + "\n"
    header += "Subject: " + subject + "\n"
    header += "\n"
    header += body
 
    print "** Sending email to '" + to + "'"
     
     
    mail_server = smtplib.SMTP(SERVER, PORT)
    mail_server.starttls()
    mail_server.login(FROM_EMAIL, FROM_PWD)
    mail_server.sendmail(FROM_EMAIL, to, header)
    mail_server.quit()

    
#
# Read the program parameters
#
logger = logging.getLogger("Code Review Log")
logger.setLevel(logging.INFO)
logHandler = RotatingFileHandler('app.log',maxBytes=3000,backupCount=2)
logger.addHandler(logHandler)

parser = argparse.ArgumentParser(description="Code Review Scheduler Program")
parser.add_argument("-n", nargs="?", type=int, default=365, help="Number of (d)ays to look for log. ")
parser.add_argument("-p", nargs="?", type=str, default="ailing", help="Project name.")
parser.add_argument("-d", nargs="?", type=int, default="1", help="past n number of days since code review request")
args = parser.parse_args()
 
no_days = args.n
project = args.p
past_days = args.d

print 'Processing the scheduler against project ' + project + '....'

#
# Read the scheduler config file
#
with open('config.json') as cfg_file:
    main_config = json.load(cfg_file)

project_members=''
for p in main_config:
    if p['name'] == project:
        project_url = p['git_url']
        project_members = p['members']
        break

#
# Read the mail server config file
#
with open('pwd.json') as mailserver_file:
    mailserver_config = json.load(mailserver_file)

for p in mailserver_config:
    FROM_EMAIL = p['from_mail']
    FROM_PWD = p['from_pwd']
    SERVER = p['server']
    PORT = p['port']
       
if not os.path.exists('reviewer.json'):
    with open('reviewer.json','w+') as outfile:
        json.dump([],outfile)


# Clone the repository if not already exists
print "********* Doing project checkout **********"
if(os.path.isdir("./" + project)):
    execute_cmd("cd " + project + "; git pull")
else:
    execute_cmd("git clone " + project_url + " " + project)
print "*** Done *******"
print " "


print 'Processing the scheduler against project ' + project + '....'
#process_commits()

try:
    commits = process_commits()
 
    if len(commits) == 0:
        print 'No commits found '
    else:
        schedule_review_request(commits)
        read_email(past_days)
except Exception,e:
    print 'Error occurred. Check log for details.'
    logger.error(str(datetime.datetime.now()) + " - Error while reading mail : " + str(e) + "\n")
    logger.exception(str(e))


