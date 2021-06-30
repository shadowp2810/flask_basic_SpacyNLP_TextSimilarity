from flask import Flask, jsonify, request
from flask_restful import Api, Resource     #Api and Resource constructors
from pymongo import MongoClient
import bcrypt
import spacy

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.SimilarityDB
users = db["Users"]

def UserExists(username):
    if users.find({"Username": username}).count() == 0:
        return False
    else:
        return True
    
def verifyPW(username, password):
    if not UserExists(username):
        return False
    hashedPW = users.find({
        "Username": username
        })[0]["Password"]   #To access the first user of this username of which there is only one's password
    
    if bcrypt.hashpw(password.encode("utf8"), hashedPW) == hashedPW:
        return True
    else:
        return False
    
def countTokens(username):
    tokens = users.find({
        "Username": username
    })[0]["Tokens"]
    return tokens
    
    
class Register(Resource):
    def post(self):
        postedData = request.get_json()
        
        username = postedData["username"]
        password = postedData["password"]
        
        if UserExists(username):
            retJson = {
                "status": 301,
                "msg": "Invalid Username: Users already exists"
            }
            return jsonify(retJson)
        
        hashedPW = bcrypt.hashpw(password.encode("utf8"), bcrypt.gensalt())
        
        users.insert({
            "Username": username,
            "Password": hashedPW,
            "Tokens": 6
        })
        
        retJson = {
            "status": 200 ,
            "msg": "Success: User successfully registered to the API" ,
            "Tokens Remaining": 6
        }
        return jsonify(retJson)
    
    
class Detect(Resource):
    def post(self):
        postedData = request.get_json()
        
        username = postedData["username"]
        password = postedData["password"]
        text1 = postedData["text1"]
        text2 = postedData["text2"]
        
        if not UserExists(username):
            retJson = {
                "status": 301,
                "msg": "Invalid Username: Users already exists"
            }
            return jsonify(retJson)

        correctPW = verifyPW(username, password)    
        
        if not correctPW:
            retJson = {
                "status": 302,
                "msg": "Invalid Password. Try again."
            } 
            return jsonify(retJson)
        
        num_tokens = countTokens(username)      
        
        if num_tokens <= 0 :
            retJson = {
                "status": 303,
                "msg": "Out of Tokens. Please Refill."
            }
            return jsonify(retJson)
        
        #Calculate the edit distance
        nlp = spacy.load('en_core_web_sm')
        
        text1 = nlp(text1)
        text2 = nlp(text2)
        
        #Ratio is between 0 and 1. Closer to 1 means more similar. 
        ratio = text1.similarity(text2)
        percent = str(ratio * 100) + " %"
        
        currentTokens = countTokens(username)   

        retJson = {
            "status": 200 ,
            "similarity": percent ,
            "msg": "Successfully calculated similarity score!" ,
            "Tokens Remaining": currentTokens-1
        }   
                
        users.update({
            "Username": username
        }, {
            "$set": {
                "Tokens": currentTokens-1
            }
        })
        
        return jsonify(retJson)


class Refill(Resource):
    def post(self):
        postedData = request.get_json()
        
        username = postedData["username"]
        password = postedData["refill_password"]
        refillAmount = postedData["refill_amount"]
        
        if not UserExists(username):
            retJson = {
                "status": 301,
                "msg": "Invalid Username: Users already exists"
            }
            return jsonify(retJson)
        
        refillPW = "refill123"    #TODO: api to set adminPW
        
        if not password == refillPW:
            retJson = {
                "status": 304,
                "msg": "Invalid refill password."
            }
            return jsonify(retJson)
        
        currentTokens = countTokens(username)
        
        users.update({
           "Username": username 
        }, {
            "$set": {
                "Tokens": refillAmount + currentTokens
            }
        })
        
        retJson = {
            "status": 200,
            "msg": "Successfully Refilled Tokens",
            "Tokens Remaining": countTokens(username)
        }
        return jsonify(retJson)

api.add_resource(Register, '/register')
api.add_resource(Detect, '/detect')
api.add_resource(Refill, '/refill')

if __name__=="__main__":
    app.run( host = "0.0.0.0" , debug=True)
    
    
    
# To run without docker
# in folder say `export FLASK_APP=app.py`
# then `flask run`

# `sudo lsof -i :5000` to find running processes on port
# `kill -9 <pid>`

        