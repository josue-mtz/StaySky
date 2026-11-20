db = db.getSiblingDB('staysky');

db.createCollection('cities');
db.createCollection('flights');
db.createCollection('hotels');
db.createCollection('weather');
db.createCollection('searches');

print('Colecciones inicializadas: cities, flights, hotels, weather, searches');