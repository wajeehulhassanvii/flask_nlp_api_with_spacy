from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import spacy

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.SimilarityDB
users = db['Users']

def user_exists(username):
    """return if user exists or not"""
    if users.find({"Username": username}).count() == 0:
        return False
    else:
        return True


class Register(Resource):
    def post(self):
        """Post method for user login"""
        posted_data = request.get_json()

        username = posted_data['username']
        password = posted_data['password']

        if user_exists(username):
            retJson = {
                "status": 301,
                "msg": "Invalid Username"
            }
            return jsonify(retJson)

        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Tokens": 6
        })

        retJson = {
            "status": 200,
            "msg": "You have successfully signed up to  the chat API"
        }
        return jsonify(retJson)


def verify_pw(username, password):
    if not user_exists(username):
        return False

    hashed_pw = users.find({
        "Username":username
    })[0]['Password']

    if bcrypt.hashpw(password.encode('utf8'), hashed_pw)==hashed_pw:
        return True
    else:
        return False


def count_tokens(username):
    tokens = users.find({
        "Username": username
    })[0]['Tokens']
    return tokens


class Detect(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data['username']
        password = posted_data['password']
        text1 = posted_data['text1']
        text2 = posted_data['text2']

        if not user_exists(username):
            retJson = {
                "status": 301,
                "msg": "Invalid Username"
            }
            return jsonify(retJson)
        correct_pw = verify_pw(username, password)

        if not correct_pw:
            return jsonify({
                'status': 302,
                "msg": "Invalid Password"
            })

        num_tokens = count_tokens(username)

        if num_tokens <= 0:
            retJson = {
                "status": 303,
                "msg": "You are out of tokens please refill"
            }
            return jsonify(retJson)

        # calculate the edit distance
        nlp = spacy.load('en_core_web_sm')

        text1 = nlp(text1)
        text2 = nlp(text2)

        # Ratio closer to 1 means similar otherwise if its closer to 0
        # then they're different
        ratio = text1.similarity(text2)

        users.update({
            "Username": username,},{
                "$set":{
                    "Tokens": count_tokens(username)-1
                }
            }
                     )

        return jsonify(
            {
                'status': 200,
                "similarity": ratio,
                "msg": "Similarity score calculated successfully"
            }
        )


class Refill(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data['username']
        password = posted_data['admin_pw']
        refill_amount = posted_data['refill']

        if not user_exists(username):
            retJson = {
                "status":301,
                "msg": "Invalid Username"
            }
            return jsonify(retJson)

        correct_pw = "abc123"
        if not password == correct_pw:
            retJson = {
                "status":304,
                "msg": "Invalid Admin Password"
            }
            return jsonify(retJson)

        current_tokens = count_tokens(username)
        users.update({
            "Username":username
        },{
            "$set":{
                "Tokens": refill_amount+current_tokens
            }
        })
        return jsonify({
            'status': 200,
            'msg': 'refilled successfully'
        })


api.add_resource(Register, '/register')
api.add_resource(Detect, '/detect')
api.add_resource(Refill, '/refill')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5000")