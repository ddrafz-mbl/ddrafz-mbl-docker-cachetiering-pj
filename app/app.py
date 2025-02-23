from flask import Flask, jsonify, Response, request
import pymongo
import pylibmc
import redis
import json


app = Flask(__name__)

# Connect to Memcached (L1)
MEMCACHED_NODES = ['memcached:11211']

mc = pylibmc.Client(MEMCACHED_NODES, binary=True, behaviors={"tcp_nodelay": True, "ketama": True})

# Connect to Redis (L2)
redis_client = redis.StrictRedis(host='redis', port=6379, decode_responses=True)

# Connect to MongoDB
def get_mongo_client():
    return pymongo.MongoClient('mongodb://mongo:27017/')


# ---------------------- Get User ----------------------
@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    cache_key = f"user:{user_id}"
    
    try:
        # Check in Memcached (L1)
        user_data = mc.get(cache_key)
        if user_data:
            print("Found in Memcached")
            response_data = {"source": "Memcached", "data": eval(user_data)}
            return Response(json.dumps(response_data, indent=4), mimetype='application/json')
    except Exception as e:
        print(f"Memcached error: {e}")
        # Fallback to Redis and MongoDB if Memcached is down
        pass
    
    # Check in Redis (L2)
    user_data = redis_client.get(cache_key)
    if user_data:
        print("Found in Redis")
        try:
            mc.set(cache_key, user_data, time=3600)  # Populate Memcached if it's back online
        except Exception as e:
            print(f"Failed to populate Memcached: {e}")
        response_data = {"source": "Redis", "data": eval(user_data)}
        return Response(json.dumps(response_data, indent=4), mimetype='application/json')
    
    # Fetch from MongoDB
    print("Not found in cache, fetching from MongoDB...")
    client = get_mongo_client()
    db = client['userdb']
    collection = db['users']
    result = collection.find_one({"id": user_id}, {"_id": 0})
    if result:
        try:
            mc.set(cache_key, str(result), time=3600)  # Populate Memcached if it back online
        except Exception as e:
            print(f"Failed to populate Memcached: {e}")
        redis_client.set(cache_key, str(result), ex=3600)  # Populate Redis
        response_data = {"source": "MongoDB", "data": result}
        return Response(json.dumps(response_data, indent=4), mimetype='application/json')
    else:
        return jsonify({"error": "User not found"}), 404

# ---------------------- Update all user cache----------------------
def update_all_users_cache():
    """Update the 'all_users' cache in Redis with the latest data from MongoDB."""
    client = get_mongo_client()
    db = client['userdb']
    collection = db['users']
    users = list(collection.find({}, {"_id": 0}))  # Fetch all users from MongoDB
    
    cache_key = "all_users"
    try:
        redis_client.set(cache_key, json.dumps(users), ex=3600)  # Cache for 1 hour
        print("Updated 'all_users' cache in Redis")
    except Exception as e:
        print(f"Failed to update Redis: {e}")


# ---------------------- Add User ----------------------
@app.route('/add_user', methods=['POST'])
def add_user():
    data = request.json
    user_id = data.get("id")
    name = data.get("name")
    email = data.get("email")
    
    if not user_id or not name or not email:
        return jsonify({"error": "Missing required fields (id, name, email)"}), 400
    
    client = get_mongo_client()
    db = client['userdb']
    collection = db['users']
    
    existing_user = collection.find_one({"id": user_id})
    if existing_user:
        return jsonify({"error": f"User with ID {user_id} already exists"}), 409
    
    result = collection.insert_one({"id": user_id, "name": name, "email": email})
    if result.inserted_id:


        cache_key = f"user:{user_id}"
        try:
            mc.set(cache_key, str(data), time=3600)  # Update Memcached
        except Exception as e:
            print(f"Failed to update Memcached: {e}")
        
        try:
            redis_client.set(cache_key, str(data), ex=3600)  # Update Redis
        except Exception as e:
            print(f"Redis is down: {e}")
        
        # Update 'all_users' cache in Redis
        update_all_users_cache()
        
        return jsonify({"message": "User added successfully", "data": data}), 201
    else:
        return jsonify({"error": "Failed to add user"}), 500
    

# ---------------------- Edit User ----------------------
@app.route('/edit_user/<int:user_id>', methods=['PUT'])
def edit_user(user_id):
    data = request.json
    name = data.get("name")
    email = data.get("email")
    
    client = get_mongo_client()
    db = client['userdb']
    collection = db['users']
    
    existing_user = collection.find_one({"id": user_id})
    if not existing_user:
        return jsonify({"error": f"User with ID {user_id} does not exist"}), 404
    
    update_data = {}
    if name:
        update_data["name"] = name
    if email:
        update_data["email"] = email
    if not update_data:
        return jsonify({"error": "No fields to update"}), 400
    
    result = collection.update_one({"id": user_id}, {"$set": update_data})
    updated_user = collection.find_one({"id": user_id}, {"_id": 0})
    
    cache_key = f"user:{user_id}"
    try:
        mc.set(cache_key, str(updated_user), time=3600)  # Update Memcached
    except Exception as e:
        print(f"Failed to update Memcached: {e}")
    
    try:
        redis_client.set(cache_key, str(updated_user), ex=3600)  # Update Redis
    except Exception as e:
        print(f"Redis is down: {e}")
    
    # Update 'all_users' cache in Redis
    update_all_users_cache()
    
    if result.modified_count > 0:
        return jsonify({"message": f"User with ID {user_id} updated successfully", "data": update_data}), 200
    else:
        return jsonify({"message": f"No changes made to user with ID {user_id}"}), 200
    

# ---------------------- Delete User ----------------------
@app.route('/delete_user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    client = get_mongo_client()
    db = client['userdb']
    collection = db['users']
    
    existing_user = collection.find_one({"id": user_id})
    if not existing_user:
        return jsonify({"error": f"User with ID {user_id} does not exist"}), 404
    
    cache_key = f"user:{user_id}"
    try:
        mc.delete(cache_key)  # Delete from Memcached
    except Exception as e:
        print(f"Failed to delete from Memcached: {e}")
    
    try:
        redis_client.delete(cache_key)  # Delete from Redis
    except Exception as e:
        print(f"Redis is down: {e}")
    
    result = collection.delete_one({"id": user_id})
    if result.deleted_count > 0:
        
        # Update 'all_users' cache in Redis
        update_all_users_cache()
        
        return jsonify({"message": f"User with ID {user_id} deleted successfully"}), 200
    else:
        return jsonify({"error": f"Failed to delete user with ID {user_id}"}), 500
    

# ---------------------- List user all http://localhost:5000/users ----------------------
@app.route('/users', methods=['GET'])
def get_all_users():
    # Define a cache key for all users
    cache_key = "all_users"
    
    try:
        # Check in Redis (L2)
        cached_data = redis_client.get(cache_key)
        if cached_data:
            print("Found in Redis")
            response_data = {"source": "Redis", "data": json.loads(cached_data)}
            return Response(json.dumps(response_data, indent=4), mimetype='application/json')
    except Exception as e:
        print(f"Redis is down: {e}")
    
    # If not found in Redis, fetch from MongoDB
    print("Not found in Redis, fetching from MongoDB...")
    client = get_mongo_client()
    db = client['userdb']
    collection = db['users']
    users = list(collection.find({}, {"_id": 0}))  # Exclude _id field
    
    try:
        # Populate Redis with the fetched data
        redis_client.set(cache_key, json.dumps(users), ex=3600)  # Cache for 1 hour
    except Exception as e:
        print(f"Failed to populate Redis: {e}")
    
    # Format and return the response
    response_data = {
        "source": "MongoDB",
        "data": users
    }
    return Response(json.dumps(response_data, indent=4), mimetype='application/json'), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)