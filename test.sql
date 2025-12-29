-- ============================================================================
-- Database Migration: Add Scheduling Feature
-- ============================================================================
-- Run this if you have an EXISTING database
-- For new installations, db.create_all() handles everything

-- ============================================================================
-- POSTGRESQL VERSION
-- ============================================================================

-- Add proposed_encounter table
CREATE TABLE IF NOT EXISTS proposed_encounter (
    id SERIAL PRIMARY KEY,
    proposer_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    partner_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    proposed_date DATE NOT NULL,
    proposed_time TIME,
    position VARCHAR(50),
    notes TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    decline_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP
);

-- Add proposed_encounter_id to notification table
ALTER TABLE notification 
ADD COLUMN IF NOT EXISTS proposed_encounter_id INTEGER REFERENCES proposed_encounter(id) ON DELETE SET NULL;

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_proposed_encounter_proposer ON proposed_encounter(proposer_id);
CREATE INDEX IF NOT EXISTS idx_proposed_encounter_partner ON proposed_encounter(partner_id);
CREATE INDEX IF NOT EXISTS idx_proposed_encounter_status ON proposed_encounter(status);
CREATE INDEX IF NOT EXISTS idx_notification_proposed_encounter ON notification(proposed_encounter_id);

-- ============================================================================
-- SQLITE VERSION
-- ============================================================================

-- For SQLite, use this instead:
/*
CREATE TABLE IF NOT EXISTS proposed_encounter (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposer_id INTEGER NOT NULL,
    partner_id INTEGER NOT NULL,
    proposed_date DATE NOT NULL,
    proposed_time TIME,
    position VARCHAR(50),
    notes TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    decline_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    FOREIGN KEY (proposer_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (partner_id) REFERENCES user(id) ON DELETE CASCADE
);

-- SQLite doesn't support ADD COLUMN IF NOT EXISTS, so check first:
-- ALTER TABLE notification ADD COLUMN proposed_encounter_id INTEGER REFERENCES proposed_encounter(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_proposed_encounter_proposer ON proposed_encounter(proposer_id);
CREATE INDEX IF NOT EXISTS idx_proposed_encounter_partner ON proposed_encounter(partner_id);
CREATE INDEX IF NOT EXISTS idx_proposed_encounter_status ON proposed_encounter(status);
CREATE INDEX IF NOT EXISTS idx_notification_proposed_encounter ON notification(proposed_encounter_id);
*/

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check if tables were created
SELECT table_name FROM information_schema.tables 
WHERE table_name = 'proposed_encounter';

-- Check if column was added
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'notification' AND column_name = 'proposed_encounter_id';

-- For SQLite verification:
-- SELECT name FROM sqlite_master WHERE type='table' AND name='proposed_encounter';
-- PRAGMA table_info(notification);
