db = db.getSiblingDB('userdb');

// Create Collection and Insert DATA
db.users.insertMany([
    { id: 1, name: "Admin Dev", email: "Admin@exp.com" },
    { id: 2, name: "D DraFz", email: "ddrafzth@gmail.com" },
    { id: 3, name: "AVA LIS", email: "AVA@LLD.com" },
    { id: 4, name: "pps_ly", email: "pps@fin.com" }
]);