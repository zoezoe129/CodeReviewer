import argparse
import json
import os
import re
import random
import time
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

def format_review_commit(commit):
    review_req = ""
    review_req += "URL:     " + project_url + '/commit/' +  commit.Id + "\n"
    review_req += "Commit:  " + commit.Id + "\n"
    review_req += "Author:  " + commit.Author + "\n"
    review_req += "Date:    " + commit.Date + "\n"
    return review_req

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

def execute_cmd(cmd):
    print "***** Executing command '"+ cmd + "'"
    response = os.popen(cmd).read()
    return response
  
def process_commits():
    cmd = "cd " + project + "; git log --all --since=" + str(no_days) + ".day --name-status"
    response = execute_cmd(cmd)
    print response
    
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
            commitId = line.split(' ')[1]
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



parser = argparse.ArgumentParser(description="Code Review Scheduler Program")
parser.add_argument("-n", nargs="?", type=int, default=365, help="Number of (d)ays to look for log. ")
parser.add_argument("-p", nargs="?", type=str, default="project_x", help="Project name.")
args = parser.parse_args()
 
no_days = args.n
project = args.p

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
schedule_review_request(process_commits())
