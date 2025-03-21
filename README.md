# Docker Cache Tiering - Python Flask, NGINX, Memcached, Redis, MongoDB

## Project Overview
* This project is designed to cache user data using a cache tiering technique between Memcached (L1) and Redis (L2), running on Docker.

## How It Works
* Users send requests through an NGINX load balancer with 3 nodes (round-robin strategy) to distribute traffic evenly.
* The request first checks L1 (Memcached) for cached data.
* If the data is not found in L1, it query L2 (Redis).
* If the data is still not available in L2, it fetches it from DB.
* The DB return the data, and the system store it in both L2 (Redis) and L1 (Memcached) for future requests.

## Failure Scenarios
* If L1 (Memcached) is down, requests will still fetch data from L2 (Redis).
* When L1 is back online, it resumes normal operations.
* If L2 (Redis) is down but data exists in L1, the system continues working normally.
* If both L1 and L2 are down, the cache system fails-urgent action is required.

## Diagram
![Docker Cache Tiering](docker-cachetiering-diagram1.png)

## Structure docker cache tiering
memcached-lab/ \
├── app/ \
│   ├── app.py \
│   │── Dockerfile \
│   └── requirements.txt \
├── conf.d/ \
│   └── nginx.conf \
├── cache_redis/ \
├── logs/ \
│   └── nginx/ \
├── init-mongo.js \
├── docker-compose.yml \
└── README.md

## if cloned into server, please rename ddrafz-mbl-docker-cachetiering-pj to memcached-lab
```
mv ddrafz-mbl-docker-cachetiering-pj memcached-lab
```
```
cd memcached-lab
```
Run docker compose:

build test to see logs:
```
docker compose up --build --scale web=3
```
build to detach:
```
docker compose up --build --scale web=3 -d
```
Open web browser:
List users All:
```
http://localhost:5000/users
```
User 1-4:
```
http://localhost:5000/user/1
```
```
http://localhost:5000/user/2
```
```
http://localhost:5000/user/3
```
```
http://localhost:5000/user/4
```

Edit user 1:
```
curl -X PUT http://localhost:5000/edit_user/1 -H "Content-Type: application/json" -d '{"id":1,"name":"criminal","email":"criminal@admin.com"}'
```
Add User 5:
```
curl -X POST http://localhost:5000/add_user -H "Content-Type: application/json" -d '{"id":5,"name":"accord prom","email":"accord@unidev.com"}'
```
## Check cached in Redis
Use docker exec in terminal:
```
docker exec -it memcached-lab-redis-1 sh
```
In redis:
```
redis-cli
```
Check users:
```
keys *
```
```
get user:1
```
```
get user:2
```
```
get user:3
```
```
get user:4
```
Delete User 1-5:
```
curl -X DELETE http://localhost:5000/delete_user/1
```
```
curl -X DELETE http://localhost:5000/delete_user/2
```
```
curl -X DELETE http://localhost:5000/delete_user/3
```
```
curl -X DELETE http://localhost:5000/delete_user/4
```
```
curl -X DELETE http://localhost:5000/delete_user/5
```
## Project Consideration for Multi-Node Environment
This project is designed for a single-node environment. If you scale to multiple servers and use a Load Balancer, there will be issues with Memcached (L1) because it does not synchronize data across multiple nodes.
## Key Issue: Cache Inconsistency
* Memcached (L1) is not shared → Different nodes may have different cache data.
* Data distribution is inconsistent → Requests routed to different nodes may return outdated or missing cache.
* Cache invalidation is harder → Updating or deleting cache across multiple Memcached instances is complex.
## Solution Consideration
* If you scale horizontally (multiple servers), Redis (L2) should be the primary cache instead of Memcached.
* Use Redis Cluster or Sentinel to ensure cache consistency across nodes.
* If Memcached is still needed, consider consistent hashing to distribute data evenly. \
⚠️  Please evaluate your system architecture carefully before scaling.

## Youtube
https://youtube.com/shorts/k-ESiZKupII

## Gitlab CI/CD Pipeline
https://gitlab.com/public-delivery/docker-cachetiering

https://youtube.com/shorts/67AvuTsJXNY
