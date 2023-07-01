from flask import Flask, jsonify, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow, fields
from marshmallow import fields
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from datetime import timedelta, date
from collections import OrderedDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from os import environ
from models.user import User, UserSchema
from models.book import Book, BookSchema
from models.comment import Comment, CommentSchema
from models.review import Review, ReviewSchema
from init import db, ma, bcrypt, jwt

from blueprints.cli_bp import cli_bp
from blueprints.auth_bp import auth_bp
from blueprints.books_bp import books_bp
from blueprints.comments_bp import comments_bp

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = environ.get('DB_URI')
app.config['JWT_SECRET_KEY'] = environ.get('JWT_KEY')

db.init_app(app)
ma.init_app(app)
jwt.init_app(app)
bcrypt.init_app(app)

app.register_blueprint(cli_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(books_bp)
app.register_blueprint(comments_bp)
    

    
@app.route('/add_review', methods=['POST'])
@jwt_required()
def add_review():
    review_data = request.json

    book_id = review_data['book_id']
    book = Book.query.get(book_id)

    user_email = get_jwt_identity()
    stmt = db.select(User).filter_by(email=user_email)
    user = db.session.scalar(stmt)

    new_review = Review(
        review_content=review_data['review_content'],
        date_created=date.today(),
        username=user.username,
        book_id=review_data['book_id'],
        user_id=user.id,
        title=book.title
    )

    book = Book.query.get(review_data['book_id'])
    user.reviews.append(new_review)
    book.reviews.append(new_review)

    db.session.add(new_review)
    db.session.commit()

    return jsonify(message='Review added successfully'), 201


@app.route('/update_review', methods=['PUT'])
@jwt_required()
def update_review():
    review_id = int(request.json['review_id'])
    review = Review.query.filter_by(review_id=review_id).first()
    if review:
        admin_or_owner_required(review.user.email)
        review.review_content=request.json['review_content'],
        review.date_created=request.json['date_created'],
        review.username=request.json['username'],
        review.book_id=int(request.json['book_id']),
        review.user_id=int(request.json['user_id']),
        review.title=request.json['title']
        db.session.commit()
        return jsonify(message="You updated a review!"), 202
    else:
        return jsonify(message="Review does not exist"), 404

    
@app.route('/delete_review/<int:review_id>', methods=['DELETE'])
@jwt_required()
def delete_review(review_id: int):
    review = Review.query.filter_by(review_id=review_id).first()
    if review:
        admin_or_owner_required(review.user.email)
        db.session.delete(review)
        db.session.commit()
        return jsonify(message="You deleted a review"), 202
    else: 
         return jsonify(message="That review does not exist"), 202


    # database model

review_schema = ReviewSchema()
reviews_schema = ReviewSchema(many=True)

comment_schema = CommentSchema()
comments_schema = CommentSchema(many=True)

user_schema = UserSchema()
users_schema = UserSchema(many=True)

book_schema = BookSchema()
books_schema = BookSchema(many=True)





if __name__ == "__main__":
    app.run(debug=True)