-----------------------------------------------------------------------------
------------------------------- User Accounts -------------------------------


-- User table
DROP TABLE IF EXISTS users CASCADE;
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    reset_code CHAR(6),
    reset_password_timer TIMESTAMP,
    two_fa_code CHAR(32),
    twofa_enabled BOOLEAN DEFAULT FALSE,
    login_attempts INTEGER DEFAULT 0,
    user_type VARCHAR(50),
    active BOOLEAN DEFAULT TRUE,
    balance NUMERIC(10, 2) DEFAULT 0
);

-- Customers table
DROP TABLE IF EXISTS customers CASCADE;
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY REFERENCES users(user_id)
);

-- Hosts table
DROP TABLE IF EXISTS hosts CASCADE;
CREATE TABLE hosts (
    host_id INTEGER PRIMARY KEY REFERENCES users(user_id),
    description TEXT,
    org_name VARCHAR(255),
    org_email VARCHAR(255),
    banner TEXT,
    num_followers INTEGER DEFAULT 0,
    rating NUMERIC(10, 2) DEFAULT 0,
    num_events INTEGER DEFAULT 0
);

-- Followers table
DROP TABLE IF EXISTS followers CASCADE;
CREATE TABLE followers (
    host_id INTEGER REFERENCES hosts(host_id),
    customer_id INTEGER REFERENCES customers(customer_id),
    PRIMARY KEY (host_id, customer_id)
);


-----------------------------------------------------------------------------
-------------------------------- Venues -------------------------------------


-- Venues table
DROP TABLE IF EXISTS venues CASCADE;
CREATE TABLE venues (
    venue_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL, 
    location_coords VARCHAR(255) NOT NULL
);

-- venue_sections table
DROP TABLE IF EXISTS venue_sections CASCADE;
CREATE TABLE venue_sections (
    section_id SERIAL PRIMARY KEY,
    venue_id INTEGER REFERENCES venues(venue_id),
    section_name VARCHAR(255) NOT NULL,
    total_seats INTEGER NOT NULL,
    CONSTRAINT unique_venue_section UNIQUE(venue_id, section_name)
);

-- venue seats
DROP TABLE IF EXISTS venue_seats CASCADE;
CREATE TABLE venue_seats (
    seat_id SERIAL PRIMARY KEY,
    seat_name VARCHAR(255),
    seat_number INTEGER,
    section_id INTEGER REFERENCES venue_sections(section_id)
);

-- Venue media table
DROP TABLE IF EXISTS venue_media CASCADE;
CREATE TABLE venue_media (
    media_id SERIAL PRIMARY KEY,
    venue_id INTEGER REFERENCES venues(venue_id),
    media_type VARCHAR(255) NOT NULL,
    media TEXT NOT NULL
);


-----------------------------------------------------------------------------
-------------------------------- Events -------------------------------------


-- Events table
DROP TABLE IF EXISTS events CASCADE;
CREATE TABLE events (
    event_id SERIAL PRIMARY KEY,
    host_id INTEGER REFERENCES hosts(host_id),
    title VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    description TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    event_capacity INT NOT NULL,
    minimum_cost NUMERIC(10, 2),
    event_type VARCHAR(100) NOT NULL,
    likes INTEGER DEFAULT 0,
    dislikes INTEGER DEFAULT 0,
    edited BOOLEAN DEFAULT FALSE,
    cancelled BOOLEAN DEFAULT FALSE,
    thumbnail TEXT,
    survey_made BOOLEAN DEFAULT FALSE
);

-- Online events table
DROP TABLE IF EXISTS online_events CASCADE;
CREATE TABLE online_events (
    online_event_id INTEGER PRIMARY KEY REFERENCES events(event_id),
    online_link VARCHAR(255),
    cost NUMERIC(10, 2),
    quantity INTEGER DEFAULT 0
);
      
-- In person seated events table
DROP TABLE IF EXISTS seated_events CASCADE;
CREATE TABLE seated_events (
    seated_event_id INTEGER PRIMARY KEY REFERENCES events(event_id),
    venue_id INTEGER REFERENCES venues(venue_id)
);

-- In person not seated events table
DROP TABLE IF EXISTS not_seated_events CASCADE;
CREATE TABLE not_seated_events (
    not_seated_event_id INTEGER PRIMARY KEY REFERENCES events(event_id),
    location VARCHAR(255) NOT NULL, 
    location_coords VARCHAR(255) NOT NULL
);


-----------------------------------------------------------------------------
-------------------------- Events - Host Input ------------------------------


-- FAQ table
DROP TABLE IF EXISTS faq CASCADE;
CREATE TABLE faq (
    faq_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id),
    question TEXT NOT NULL,
    answer TEXT NOT NULL
);

-- Event announcements table
DROP TABLE IF EXISTS event_announcements CASCADE;
CREATE TABLE event_announcements (
    announcement_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id),
    event_host INTEGER REFERENCES hosts(host_id),
    title VARCHAR(255) NOT NULL,
    date TIMESTAMP NOT NULL,
    message TEXT NOT NULL
);

-- Event media table
DROP TABLE IF EXISTS event_media CASCADE;
CREATE TABLE event_media (
    media_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id),
    media_type VARCHAR(255) NOT NULL,
    media TEXT NOT NULL
);

-- Tags table
DROP TABLE IF EXISTS tags CASCADE;
CREATE TABLE tags (
    tag_id SERIAL PRIMARY KEY,
    tag_name VARCHAR(255) NOT NULL UNIQUE
);

-- Event tags table
DROP TABLE IF EXISTS event_tags CASCADE;
CREATE TABLE event_tags (
    event_id INTEGER REFERENCES events(event_id),
    tag_id INTEGER REFERENCES tags(tag_id),
    PRIMARY KEY (event_id, tag_id)
);


-----------------------------------------------------------------------------
--------------------------- Events - User Input -----------------------------


-- Dislikes table
DROP TABLE IF EXISTS dislikes CASCADE;
CREATE TABLE dislikes (
    customer_id INTEGER REFERENCES customers(customer_id),
    event_id INTEGER REFERENCES events(event_id),
    PRIMARY KEY (customer_id, event_id)
);

-- Likes table
DROP TABLE IF EXISTS likes CASCADE;
CREATE TABLE likes (
    customer_id INTEGER REFERENCES customers(customer_id),
    event_id INTEGER REFERENCES events(event_id),
    PRIMARY KEY (customer_id, event_id)
);

-- Event Reviews table
DROP TABLE IF EXISTS event_reviews CASCADE;
CREATE TABLE event_reviews (
    review_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    event_id INTEGER REFERENCES events(event_id),
    rating INTEGER NOT NULL,
    review TEXT NOT NULL,
    date TIMESTAMP NOT NULL,
    edited BOOLEAN DEFAULT FALSE,
    likes INTEGER DEFAULT 0,
    event_host INTEGER REFERENCES hosts(host_id),
    host_replied BOOLEAN DEFAULT FALSE,
    host_reply_date TIMESTAMP,
    host_edited_reply BOOLEAN DEFAULT FALSE,
    host_reply_message TEXT
);

-- Review Likes table
DROP TABLE IF EXISTS review_likes CASCADE;
CREATE TABLE review_likes (
    user_id INTEGER REFERENCES users(user_id),
    review_id INTEGER REFERENCES event_reviews(review_id),
    PRIMARY KEY (user_id, review_id)
);

-----------------------------------------------------------------------------
------------------------ Events - Ticketing/Pricing -------------------------


-- Designates pricing/remaning tickets for different ticket types (FOR ONLINE + IN PERSON + SEATED EVENTS)
ALTER TABLE IF EXISTS event_reserves 
    DROP CONSTRAINT IF EXISTS unique_event_reserve;
DROP TABLE IF EXISTS event_reserves CASCADE;
CREATE TABLE event_reserves (
    event_reserve_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id),
    reserve_name VARCHAR(255) NOT NULL,
    reserve_description TEXT,
    cost NUMERIC(10, 2) DEFAULT 0,
    tickets_available INTEGER NOT NULL,
    CONSTRAINT unique_event_reserve UNIQUE(event_id, reserve_name)
);

-- Designates remaining tickets for each venue section (FOR SEATED EVENTS)
ALTER TABLE IF EXISTS event_sections 
    DROP CONSTRAINT IF EXISTS unique_event_section;
DROP TABLE IF EXISTS event_sections CASCADE;
CREATE TABLE event_sections (
    event_section_id SERIAL PRIMARY KEY,
    event_reserve_id INTEGER REFERENCES event_reserves(event_reserve_id),
    venue_section_id INTEGER REFERENCES venue_sections(section_id),
    tickets_available INTEGER NOT NULL,
    CONSTRAINT unique_event_section UNIQUE(venue_section_id, event_section_id)
);


-----------------------------------------------------------------------------
-------------------------------- Booking ------------------------------------


-- Booking table
DROP TABLE IF EXISTS bookings CASCADE;
CREATE TABLE bookings (
    booking_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id),
    customer_id INTEGER REFERENCES customers(customer_id),
    date TIMESTAMP NOT NULL,
    total_cost NUMERIC(10, 2) NOT NULL,
    total_quantity INTEGER NOT NULL,
    referral_code VARCHAR(255) DEFAULT '',
    amount_saved NUMERIC(10, 2) DEFAULT 0,
    cancelled BOOLEAN DEFAULT FALSE
);

-- Contains all tickets in a booking from the same reserve (FOR ONLINE + IN PERSON + SEATED EVENTS)
DROP TABLE IF EXISTS booking_reserve CASCADE;
CREATE TABLE booking_reserve (
    booking_reserve_id SERIAL PRIMARY KEY,
    booking_id INTEGER REFERENCES bookings(booking_id),
    reserve_id INTEGER REFERENCES event_reserves(event_reserve_id),
    quantity INTEGER DEFAULT 0
);

-- Seated Tickets table (SEATED EVENTS)
DROP TABLE IF EXISTS seated_tickets CASCADE;
CREATE TABLE seated_tickets (
    ticket_id SERIAL PRIMARY KEY,
    booking_reserve_id INTEGER REFERENCES booking_reserve(booking_reserve_id) NOT NULL,
    event_section_id INTEGER REFERENCES event_sections(event_section_id) NOT NULL,
    seat_id INTEGER REFERENCES venue_seats(seat_id),
    seat_name VARCHAR(255) NOT NULL
);

-----------------------------------------------------------------------------
------------------------------- Referrals -----------------------------------

DROP TABLE IF EXISTS referrals CASCADE;
CREATE TABLE referrals (
    referral_code VARCHAR(255) PRIMARY KEY,
    host_id INTEGER REFERENCES hosts(host_id) NOT NULL,
    percentage_off NUMERIC(3, 2) NOT NULL DEFAULT 0,
    referrer_cut NUMERIC(3, 2) NOT NULL DEFAULT 0,
    referrer_name VARCHAR(255) NOT NULL,
    pay_id_phone VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    amount_paid NUMERIC(10, 2) NOT NULL DEFAULT 0,
    amount_used INTEGER DEFAULT 0
);


-----------------------------------------------------------------------------
------------------------------ User Profile ---------------------------------


-- favourited events table
DROP TABLE IF EXISTS favourited_events CASCADE;
CREATE TABLE favourited_events (
    customer_id INTEGER REFERENCES customers(customer_id),
    event_id INTEGER REFERENCES events(event_id),
    PRIMARY KEY (customer_id, event_id)
);

-- Billing info table
DROP TABLE IF EXISTS billing_info CASCADE;
CREATE TABLE billing_info (
    billing_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    cardholder_name VARCHAR(255) NOT NULL,
    card_number VARCHAR(255) NOT NULL,
    expiry_month INTEGER NOT NULL,
    expiry_year INTEGER NOT NULL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    country VARCHAR(255) NOT NULL,
    street_line1 VARCHAR(255) NOT NULL,
    street_line2 VARCHAR(255),
    suburb VARCHAR(255) NOT NULL,
    state VARCHAR(255) NOT NULL,
    postcode INTEGER NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(255) NOT NULL
);


-----------------------------------------------------------------------------
--------------------------- User Transactions -------------------------------


DROP TABLE IF EXISTS transaction CASCADE;
CREATE TABLE transaction (
    transaction_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    date TIMESTAMP NOT NULL,
    description TEXT NOT NULL,
    credit NUMERIC(10, 2) NOT NULL DEFAULT 0,
    debit NUMERIC(10, 2) NOT NULL DEFAULT 0,
    balance NUMERIC(10, 2) DEFAULT 0
);

-----------------------------------------------------------------------------
------------------------------ Event Chat -----------------------------------


-- Create chat_messages table
DROP TABLE IF EXISTS chat_messages CASCADE;
CREATE TABLE chat_messages (
    message_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id),
    user_id INTEGER REFERENCES users(user_id),
    message TEXT NOT NULL,
    likes INTEGER NOT NULL DEFAULT 0,
    time_sent TIMESTAMP NOT NULL, 
    reply_to INTEGER REFERENCES chat_messages(message_id),
    edited BOOLEAN NOT NULL DEFAULT FALSE,
    pinned BOOLEAN NOT NULL DEFAULT FALSE,
    deleted BOOLEAN DEFAULT FALSE,
    files TEXT ARRAY
);

-- Create chat_likes table
DROP TABLE IF EXISTS chat_likes CASCADE;
CREATE TABLE chat_likes (
    message_id INTEGER REFERENCES chat_messages(message_id),
    user_id INTEGER REFERENCES users(user_id),
    PRIMARY KEY (message_id, user_id)
);

-----------------------------------------------------------------------------
-------------------------------- SURVEY -------------------------------------

-- SURVEY 
DROP TABLE IF EXISTS survey CASCADE;
CREATE TABLE survey (
    survey_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id),
    host_id INTEGER REFERENCES hosts(host_id)
);

-- SURVEY QUESTIONS
DROP TABLE IF EXISTS survey_question CASCADE;
CREATE TABLE survey_question (
    survey_question_id SERIAL PRIMARY KEY,
    question VARCHAR(255),
    survey_id INTEGER REFERENCES survey(survey_id),
    short_input BOOLEAN
);

-- SURVEY RESPONSE
DROP TABLE IF EXISTS survey_responses CASCADE;
CREATE TABLE survey_responses (
    customer_id INTEGER REFERENCES customers(customer_id),
    survey_id INTEGER REFERENCES survey(survey_id),
    PRIMARY KEY (customer_id, survey_id)
);


-----------------------------------------------------------------------------
----------------------- Analytics Data Collection ---------------------------


DROP TABLE IF EXISTS follower_log CASCADE;
CREATE TABLE follower_log (
    host_id INTEGER REFERENCES hosts(host_id),
    date DATE NOT NULL,
    follower_count INTEGER DEFAULT 0,
    PRIMARY KEY (host_id, date)
);


DROP TABLE IF EXISTS event_sales CASCADE;
CREATE TABLE event_sales (
    host_id INTEGER REFERENCES hosts(host_id),
    event_id INTEGER REFERENCES events(event_id),
    reserve_id INTEGER REFERENCES event_reserves(event_reserve_id),
    date DATE NOT NULL,
    sales INTEGER DEFAULT 0,
    PRIMARY KEY (host_id, reserve_id, date)
);


DROP TABLE IF EXISTS host_daily_sales CASCADE;
CREATE TABLE host_daily_sales (
    host_id INTEGER REFERENCES hosts(host_id),
    date DATE NOT NULL,
    sales NUMERIC(10, 2) DEFAULT 0,
    PRIMARY KEY (host_id, date)
);
