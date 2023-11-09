CREATE TABLE user(
    id TEXT PRIMAY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    profile_pic TEXT NOT NULL
);