import psycopg2 as psycopg
from datetime import datetime
import time

try:
  connectStr = "dbname='rubitrack_dev' user='track' password='track_db' host='lula'"
  connection = psycopg.connect(connectStr)
  cursor = connection.cursor()
  print("connected to DB")
except:
  print("could not connect to the database")

file = open('/home/rubicontext/Downloads/playlist.log', 'r')
while 1:
    where = file.tell()
    line = file.readline()
    if not line:
        time.sleep(1)
        file.seek(where)
    else:
        print(line) # already has newline

        #first get the track in the registry, or insertit
        #split the line to get the track title + artist
        track_title = line.split('-')[1].lstrip().strip() #issue with preceeding white spaces lstrip().
        print("Title=",track_title,"#")
        #postgres_select_query = " SELECT id from track_track WHERE title like %s;"

        postgres_select_query = 'SELECT * from track_track tt WHERE LOWER(tt.title) LIKE LOWER(%s)'
        search_term = track_title[1:-1]
        like_pattern = '%{}%'.format(search_term)
        cursor.execute(postgres_select_query, (like_pattern,))


        #cursor.execute(postgres_select_query, (track_title,))
        track_records = cursor.fetchall()
        for row in track_records:
            print("Id = ", row[0], )
            track_id = row[0]

        postgres_insert_query = """ INSERT INTO track_currentlyplaying (date_played, track_id) VALUES (%s,%s)"""
        current_time = datetime.now()
        #track_id = 1
        record_to_insert = (current_time, track_id)
        cursor.execute(postgres_insert_query, record_to_insert)

        connection.commit()
        count = cursor.rowcount
        print (count, "Record(s) inserted successfully into currently playing table")