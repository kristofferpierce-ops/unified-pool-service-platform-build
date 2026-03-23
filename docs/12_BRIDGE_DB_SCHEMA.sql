CREATE TABLE caller_relationships (
            phone TEXT NOT NULL,
            contact_id TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 1,
            last_selected_at TEXT,
            PRIMARY KEY (phone, contact_id)
        )

CREATE TABLE calls (
            id TEXT PRIMARY KEY,
            rc_event_uuid TEXT,
            telephony_session_id TEXT,
            source_record_id TEXT,
            caller_phone TEXT,
            internal_phone TEXT,
            agent_extension_id TEXT,
            direction TEXT,
            call_time TEXT,
            summary TEXT,
            next_steps TEXT,
            transcript TEXT,
            extracted_address TEXT,
            extracted_names TEXT,
            status TEXT,
            raw_json TEXT,
            attached_contact_ids TEXT,
            created_at TEXT,
            updated_at TEXT
        , hidden INTEGER DEFAULT 0, trashed_at TEXT, trash_reason TEXT, hud_dismissed_at TEXT, last_status_code TEXT, item_type TEXT DEFAULT 'call', voicemail_message_id TEXT, voicemail_transcription_status TEXT, voicemail_duration INTEGER, voicemail_recording_uri TEXT, voicemail_transcription_uri TEXT, caller_name TEXT)

CREATE TABLE message_sync_state (
            scope TEXT PRIMARY KEY,
            sync_token TEXT,
            sync_time TEXT,
            updated_at TEXT
        )

CREATE TABLE processed_event_uuids (
            event_uuid TEXT PRIMARY KEY,
            created_at TEXT
        )

CREATE TABLE routing_rules (
            phone TEXT PRIMARY KEY,
            label TEXT,
            mode TEXT NOT NULL DEFAULT 'manual',
            owner_type TEXT NOT NULL DEFAULT 'unknown',
            default_contact_ids TEXT,
            notes TEXT,
            updated_at TEXT
        )

CREATE TABLE sms_batches (
            id TEXT PRIMARY KEY,
            batch_date TEXT NOT NULL,
            external_phone TEXT NOT NULL,
            internal_phone TEXT,
            latest_message_at TEXT,
            status TEXT,
            summary TEXT,
            next_steps TEXT,
            transcript TEXT,
            extracted_address TEXT,
            extracted_names TEXT,
            attached_contact_ids TEXT,
            auto_attached INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        , hidden INTEGER DEFAULT 0, trashed_at TEXT, trash_reason TEXT)

CREATE TABLE sms_messages (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            message_time TEXT,
            direction TEXT,
            from_phone TEXT,
            to_phone TEXT,
            body TEXT,
            raw_json TEXT,
            created_at TEXT,
            FOREIGN KEY(batch_id) REFERENCES sms_batches(id)
        )
