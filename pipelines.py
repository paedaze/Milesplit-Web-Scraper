import sqlite3

class AthleteDatabasePipeline:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def process_item(self, item, spider):
        try:
            self.conn = sqlite3.connect('athletes.db')
            self.cursor = self.conn.cursor()

            # Find school_id from school_name
            self.cursor.execute("SELECT school_id FROM schools WHERE school_name = ?", (item['school_name'].strip(),))
            school_row = self.cursor.fetchone()
            if not school_row:
                return
            school_id = school_row[0]

            # Check if the athlete has already been inserted into the database
            # (conditions: athlete name = name in database, school name = school assigned to said athlete)
            self.cursor.execute("""
                SELECT a.athlete_id
                FROM athletes a
                JOIN results r ON a.athlete_id = r.athlete_id
                WHERE a.name = ? AND r.school_id = ?
            """, (item['athlete_name'], school_id))
            existing_row = self.cursor.fetchone()

            athlete_id = None

            # Does not insert another athlete if they already exist, else it inserts new athlete entry into the database
            if existing_row:
                athlete_id = existing_row[0]
            else:
                # Insert athlete entry and Find athlete_id from athlete_name
                self.cursor.execute("INSERT OR IGNORE INTO athletes (name) VALUES (?)", (item['athlete_name'],))
                self.cursor.execute("SELECT athlete_id FROM athletes WHERE name = ?", (item['athlete_name'],))
                athlete_row = self.cursor.fetchone()
                if not athlete_row:
                    return
                athlete_id = athlete_row[0]

            # Find gender_id from gender
            self.cursor.execute("SELECT gender_id FROM genders WHERE gender = ?", (item['gender'],))
            gender_row = self.cursor.fetchone()
            if not gender_row:
                return
            gender_id = gender_row[0]

            # Find event_id from event_name
            self.cursor.execute("SELECT event_id FROM events WHERE event_name = ?", (item['event_name'],))
            event_row = self.cursor.fetchone()
            if not event_row:
                return
            event_id = event_row[0]

            # Insert data into results
            self.cursor.execute('''
                INSERT OR REPLACE INTO results (athlete_id, event_id, school_id, gender_id, time)
                VALUES (?, ?, ?, ?, ?)''', 
                (athlete_id, event_id, school_id, gender_id, item['event_time']))
            
            self.conn.commit()
            self.conn.close()
        except sqlite3.Error as e:
            spider.logger.error(f"Database error: {e} - Item: {item}")
    

        
