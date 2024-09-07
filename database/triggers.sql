-- average rating for host and event

-----------------------------------------------------------------------------
---------------------------- Event Reactions -------------------------------

-- Trigger to update event likes
CREATE OR REPLACE FUNCTION update_event_likes()
RETURNS TRIGGER AS $$
BEGIN
   CASE TG_OP
   WHEN 'INSERT' THEN
        UPDATE events AS e
        SET    likes = likes + 1
        WHERE  e.event_id = NEW.event_id;

        -- check if the user previously disliked this event
        IF EXISTS (SELECT 1 FROM dislikes WHERE customer_id = NEW.customer_id AND event_id = NEW.event_id) THEN
            UPDATE events AS e
            SET    dislikes = dislikes - 1
            WHERE  e.event_id = NEW.event_id
            AND    e.dislikes > 0;

            -- remove the previous dislike
            DELETE FROM dislikes WHERE customer_id = NEW.customer_id AND event_id = NEW.event_id;
        END IF;
   WHEN 'DELETE' THEN
        UPDATE events AS e
        SET    likes = likes - 1 
        WHERE  e.event_id = OLD.event_id
        AND    e.likes > 0;
   ELSE
        RAISE EXCEPTION 'Unexpected TG_OP: "%". Should not occur!', TG_OP;
   END CASE;
   RETURN NULL;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_likes
AFTER INSERT OR DELETE ON likes
FOR EACH ROW EXECUTE PROCEDURE update_event_likes();

-- Trigger to update event dislikes
CREATE OR REPLACE FUNCTION update_event_dislikes()
RETURNS TRIGGER AS $$
BEGIN
   CASE TG_OP
   WHEN 'INSERT' THEN
        UPDATE events AS e
        SET    dislikes = dislikes + 1
        WHERE  e.event_id = NEW.event_id;

        -- check if the user previously liked this event
        IF EXISTS (SELECT 1 FROM likes WHERE customer_id = NEW.customer_id AND event_id = NEW.event_id) THEN
            UPDATE events AS e
            SET    likes = likes - 1
            WHERE  e.event_id = NEW.event_id
            AND    e.likes > 0;

            -- remove the previous like
            DELETE FROM likes WHERE customer_id = NEW.customer_id AND event_id = NEW.event_id;
        END IF;
   WHEN 'DELETE' THEN
        UPDATE events AS e
        SET    dislikes = dislikes - 1 
        WHERE  e.event_id = OLD.event_id
        AND    e.dislikes > 0;
   ELSE
        RAISE EXCEPTION 'Unexpected TG_OP: "%". Should not occur!', TG_OP;
   END CASE;
   RETURN NULL;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_dislikes
AFTER INSERT OR DELETE ON dislikes
FOR EACH ROW EXECUTE PROCEDURE update_event_dislikes();


-----------------------------------------------------------------------------
------------------------------ Host Followers -------------------------------

-- Trigger to update followers
CREATE OR REPLACE FUNCTION update_host_followers()
RETURNS TRIGGER AS $$
BEGIN
   CASE TG_OP
   WHEN 'INSERT' THEN
        UPDATE hosts AS h
        SET    num_followers = num_followers + 1
        WHERE  h.host_id = NEW.host_id;
   WHEN 'DELETE' THEN
        UPDATE hosts AS h
        SET    num_followers = num_followers - 1 
        WHERE  h.host_id = OLD.host_id
        AND    h.num_followers > 0;
   ELSE
        RAISE EXCEPTION 'Unexpected TG_OP: "%". Should not occur!', TG_OP;
   END CASE;
   RETURN NULL;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_host_followers
AFTER INSERT OR DELETE ON followers
FOR EACH ROW EXECUTE PROCEDURE update_host_followers();


-----------------------------------------------------------------------------
--------------------------- Event Available Tickets -------------------------

-- for all events
CREATE OR REPLACE FUNCTION update_available_reserve_tickets()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE event_reserves
        SET tickets_available = tickets_available - NEW.quantity
        WHERE event_reserve_id = NEW.reserve_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE event_reserves
        SET tickets_available = tickets_available + OLD.quantity
        WHERE event_reserve_id = OLD.reserve_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER update_available_tickets_in_event_reserve
AFTER INSERT OR DELETE ON booking_reserve
FOR EACH ROW
EXECUTE FUNCTION update_available_reserve_tickets();


-- for seated events
CREATE OR REPLACE FUNCTION update_available_section_tickets()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE event_sections as e
        SET tickets_available = tickets_available - 1
        WHERE e.event_section_id = NEW.event_section_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE event_sections as e
        SET tickets_available = tickets_available + 1
        WHERE e.event_section_id = OLD.event_section_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER update_available_tickets_in_event_section
AFTER INSERT OR DELETE ON seated_tickets
FOR EACH ROW
EXECUTE FUNCTION update_available_section_tickets();
-----------------------------------------------------------------------------
--------------------------- Update no of events -----------------------------

-- Trigger to calculate the average host rating
CREATE OR REPLACE FUNCTION update_num_events()
RETURNS TRIGGER AS $$
BEGIN
   CASE TG_OP
   WHEN 'INSERT' THEN
        UPDATE hosts AS h
        SET    num_events = num_events + 1
        WHERE  h.host_id = NEW.host_id;
   WHEN 'DELETE' THEN
        UPDATE hosts AS h
        SET    num_events = num_events - 1 
        WHERE  h.host_id = OLD.host_id
        AND    h.num_events > 0;
   ELSE
        RAISE EXCEPTION 'Unexpected TG_OP: "%". Should not occur!', TG_OP;
   END CASE;
   RETURN NULL;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_num_events
AFTER INSERT OR DELETE ON events
FOR EACH ROW EXECUTE PROCEDURE update_num_events();

-----------------------------------------------------------------------------
------------------------------ Average Rating -------------------------------

CREATE OR REPLACE FUNCTION update_host_average_rating()
RETURNS TRIGGER AS
$$
DECLARE
    total_rating INTEGER;
    review_count INTEGER;
    avg_rating NUMERIC(10, 2);
BEGIN
    SELECT SUM(rating), COUNT(*) INTO total_rating, review_count
    FROM event_reviews
    WHERE event_host = NEW.event_host;
    
    IF review_count > 0 THEN
        avg_rating := total_rating::NUMERIC / review_count;
    ELSE
        avg_rating := 0;
    END IF;
    
    UPDATE hosts
    SET rating = avg_rating
    WHERE host_id = NEW.event_host;
    
    RETURN NEW;
END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER calculate_average_rating
AFTER INSERT OR UPDATE ON event_reviews
FOR EACH ROW
EXECUTE FUNCTION update_host_average_rating();

-----------------------------------------------------------------------------
-------------------------------- Event Chat ---------------------------------

-- Trigger to update message likes
CREATE OR REPLACE FUNCTION update_message_likes()
RETURNS TRIGGER AS $$
BEGIN
   CASE TG_OP
   WHEN 'INSERT' THEN
        UPDATE chat_messages AS e
        SET    likes = likes + 1
        WHERE  e.message_id = NEW.message_id;
   WHEN 'DELETE' THEN
        UPDATE chat_messages AS e
        SET    likes = likes - 1 
        WHERE  e.message_id = OLD.message_id
        AND    e.likes > 0;
   ELSE
        RAISE EXCEPTION 'Unexpected TG_OP: "%". Should not occur!', TG_OP;
   END CASE;
   RETURN NULL;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_message_likes
AFTER INSERT OR DELETE ON chat_likes
FOR EACH ROW EXECUTE PROCEDURE update_message_likes();
------------------------------ Review Likes ---------------------------------
CREATE OR REPLACE FUNCTION update_review_likes()
RETURNS TRIGGER AS $$
BEGIN
    CASE TG_OP
    WHEN 'INSERT' THEN
        UPDATE event_reviews AS e
        SET    likes = likes + 1
        WHERE  e.review_id = NEW.review_id;

    WHEN 'DELETE' THEN
        UPDATE event_reviews AS e
        SET    likes = likes - 1 
        WHERE  e.review_id = OLD.review_id
        AND    e.likes > 0;
    ELSE
        RAISE EXCEPTION 'Unexpected TG_OP: "%". Should not occur!', TG_OP;
    END CASE;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_review_likes_trigger
AFTER INSERT OR DELETE
ON review_likes
FOR EACH ROW EXECUTE PROCEDURE update_review_likes();
