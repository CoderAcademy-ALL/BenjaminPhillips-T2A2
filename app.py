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
import psycopg2
from init import db, ma, bcrypt, jwt

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = environ.get('DB_URI')
app.config['JWT_SECRET_KEY'] = environ.get('JWT_KEY')

db.init_app(app)
ma.init_app(app)
jwt.init_app(app)
bcrypt.init_app(app)






@app.cli.command('db_create')
def db_create():
    db.drop_all() 
    db.create_all()
    print('Database created successfully')


@app.cli.command('db_seed')    
def db_seed():
    books = [
        Book(
        title='King James Bible',
        genre='Religion',
        author='Various',
        synopsis="The Old Testament tells the story of God's chosen people, the Hebrews. The New Testament tells of Jesus' birth, life, ministry, death and resurrection, the growth of the early Christian Church, and predictions of the second coming of Jesus.",
        publication_year=1611),
        Book(
        title='The Lord of the Rings',
        genre='High Fantasy',
        author='JRR Tolkien',
        synopsis='In order to defeat the dark lord Sauron, Frodo Baggins is tasked with destroying the one ring',
        publication_year=1954),
        Book(
        title='Dracula',
        genre='Gothic Horror',
        author='Bram Stoker',
        synopsis='Follows the story of Count Dracula, a vampire from Transylvania, as he seeks to spread his curse and terrorize Victorian England.',
        publication_year=1954),
    ]

    db.session.add_all(books)

    test_users = [
        User(
        username='Booklover69',
        email='Booklover69@gmail.com',
        password=bcrypt.generate_password_hash('ilovebooks').decode('utf-8')),
        User(
        username='BenP',
        email='BenP@gmail.com',
        password=bcrypt.generate_password_hash('ayylmao').decode('utf-8'),
        is_admin=True)
    ]
    for user in test_users:
        db.session.add(user)

    db.session.commit()

    reviews = [
        Review(
            review_content="OMG I LOVE THIS BOOK!! SO GOOD!!",
            date_created=date.today(),
            user=test_users[0],
            book=books[1],
            username=test_users[0].username,
            title=books[1].title
        ),
        Review(
            review_content="Greatest book of all time",
            date_created=date.today(),
            user=test_users[1],
            book=books[0],
            username=test_users[1].username,
            title=books[0].title
        )
    ]

    db.session.add_all(reviews)
    db.session.commit()

    comments = [
        Comment(
            comment_content="I disagree with you, my boy",
            date_created=date.today(),
            user=test_users[1],
            review=reviews[1],
            username=test_users[1].username
        )
    ]

    db.session.add_all(comments)
    db.session.commit()

    print('Database seeded successfully')

    
def admin_or_owner_required(owner_email):
    user_email = get_jwt_identity()
    stmt = db.select(User).filter_by(email=user_email)
    user = db.session.scalar(stmt)
    if not (user and (user.is_admin or user_email == owner_email)):
        abort(401, description='You must be an admin or the owner')

    
@app.route("/books", methods=["GET"])
def books():
    books_list = Book.query.all()
    result = books_schema.dump(books_list)
    return jsonify(result)

@app.route("/register", methods=['POST'])
def register():
    email = request.form['email']
    test = User.query.filter_by(email=email).first()
    if test: 
        return jsonify(message="that email already exists"), 409
    else:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user = User(username=username, email=email, password=bcrypt.generate_password_hash(password).decode('utf8'))
        db.session.add(user)
        db.session.commit()
        return UserSchema(exclude=['password']).dump(user), 201
    
@app.route('/login', methods=['POST'])
def login():
    try:
        stmt = db.select(User).filter_by(email=request.json['email'])
        user = db.session.scalar(stmt)
        if user and bcrypt.check_password_hash(user.password, request.json['password']):
            token = create_access_token(identity=user.email, expires_delta=timedelta(days=1))
            return {'token': token, 'user': UserSchema(exclude=['password']).dump(user)}
        else:
            return {'error': 'Invalid email address or password'}, 401
    except KeyError:
        return {'error': 'Email and password are required'}, 400


@app.route('/book_details/<int:book_id>', methods=['GET'])
def book_details(book_id: int):
    book = Book.query.filter_by(book_id=book_id).first()
    if book:
        result = book_schema.dump(book)
        return jsonify(result)
    else:
        return jsonify(message="That book does not exist"), 404
    
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



@app.route("/add_comment", methods=["POST"])
@jwt_required()
def create_comment():
    
    comment_data = request.json

    comment_content = comment_data.get('comment_content')
    review_id = comment_data.get('review_id')

    user_email = get_jwt_identity()
    stmt = db.select(User).filter_by(email=user_email)
    user = db.session.scalar(stmt)

    new_comment = Comment(
        comment_content=comment_content,
        username=user.username,
        user_id=user.id,
        review_id=review_id,
        date_created=date.today()
    )

    db.session.add(new_comment)
    db.session.commit()
    return jsonify({'message': 'Comment created successfully'})


@app.route("/delete_comment/<comment_id>", methods=["DELETE"])
@jwt_required()
def delete_comment(comment_id):
    comment = Comment.query.get(comment_id)

    if comment:
        admin_or_owner_required(comment.user.email)
        db.session.delete(comment)
        db.session.commit()

        return jsonify({'message': 'Comment deleted successfully'})
    else:
        return jsonify({'message': 'Comment not found'})
    
@app.route("/edit_comment/<comment_id>", methods=["PUT"])
@jwt_required()
def edit_comment(comment_id):
    comment = Comment.query.get(comment_id)

    if comment:
        admin_or_owner_required(comment.user.email)
        data = request.get_json()
        
        comment.comment_content = data.get('comment_content')

        db.session.commit()

        return jsonify({'message': 'Comment updated successfully'})
    else:
        return jsonify({'message': 'Comment not found'})

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

@app.route('/add_book', methods=['POST'])
@jwt_required()
def add_book():
    title = request.form['title']
    test = Book.query.filter_by(title=title).first()
    if test:
        return jsonify("There is already a book with that title"), 409
    else:
        genre = request.form['genre']
        author = request.form['author']
        synopsis = request.form['synopsis']
        publication_year = int(request.form['publication_year'])

        new_book = Book(title=title, author=author, genre=genre, synopsis=synopsis, publication_year=publication_year)

        db.session.add(new_book)
        db.session.commit()
        return jsonify(message="You added a new book!"), 201

@app.route('/update_book', methods=['PUT'])
@jwt_required()
def update_book():
    book_id = int(request.form['book_id'])
    book = Book.query.filter_by(book_id=book_id).first()
    if book:
        book.title = request.form['title']
        book.author = request.form['author']
        book.genre = request.form['genre']
        book.synopsis = request.form['synopsis']
        book.publication_year = int(request.form['publication_year'])
        db.session.commit()
        return jsonify(message="You updated a book!"), 202
    else:
        return jsonify(message="Book does not exist"), 404

@app.route('/delete_book/<int:book_id>', methods=['DELETE'])
@jwt_required()
def delete_book(book_id: int):
    book = Book.query.filter_by(book_id=book_id).first()
    if book:
        db.session.delete(book)
        db.session.commit()
        return jsonify(message="You deleted a book"), 202
    else: 
         return jsonify(message="That book does not exist"), 202
    
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