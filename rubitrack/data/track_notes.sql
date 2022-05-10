
--find duplicates with same artist
select tt.title, ta.name, count(tt) 
from track_track tt left join track_artist ta on ta.id=tt.artist_id 
group by tt.title, ta.name
having count(*)>1;

--find TITLE duplicates
select tt.title, count(tt) 
from track_track tt
group by tt.title
having count(*)>1;
