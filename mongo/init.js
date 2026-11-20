db = db.getSiblingDB('staysky');

['cities','flights','hotels','weather','searches'].forEach(c => {
  if (!db.getCollectionNames().includes(c)) db.createCollection(c);
});

db.cities.createIndex({ iata: 1 }, { unique: true });
db.weather.createIndex({ city: 1, date: 1 }, { unique: true });

db.cities.insertMany([
  { iata:'CUN', name:'Cancún',            state:'Quintana Roo',       country:'MX', lat:21.1619, lon:-86.8515, timezone:'America/Cancun',     type:'playa'   },
  { iata:'MEX', name:'Ciudad de México',  state:'CDMX',               country:'MX', lat:19.4326, lon:-99.1332, timezone:'America/Mexico_City', type:'ciudad'  },
  { iata:'GDL', name:'Guadalajara',       state:'Jalisco',            country:'MX', lat:20.6597, lon:-103.3496,timezone:'America/Mexico_City', type:'ciudad'  },
  { iata:'PVR', name:'Puerto Vallarta',   state:'Jalisco',            country:'MX', lat:20.6534, lon:-105.2253,timezone:'America/Mexico_City', type:'playa'   },
  { iata:'SJD', name:'Los Cabos',         state:'Baja California Sur',country:'MX', lat:23.0588, lon:-109.6970,timezone:'America/Mazatlan',   type:'playa'   },
  { iata:'MID', name:'Mérida',            state:'Yucatán',            country:'MX', lat:20.9674, lon:-89.5926, timezone:'America/Merida',     type:'ciudad'  },
  { iata:'HUX', name:'Huatulco',          state:'Oaxaca',             country:'MX', lat:15.7749, lon:-96.2627, timezone:'America/Mexico_City', type:'playa'   },
  { iata:'ZIH', name:'Zihuatanejo',       state:'Guerrero',           country:'MX', lat:17.6417, lon:-101.5514,timezone:'America/Mexico_City', type:'playa'   },
  { iata:'MTY', name:'Monterrey',         state:'Nuevo León',         country:'MX', lat:25.6866, lon:-100.3161,timezone:'America/Monterrey',   type:'ciudad'  },
  { iata:'OAX', name:'Oaxaca',            state:'Oaxaca',             country:'MX', lat:17.0732, lon:-96.7266, timezone:'America/Mexico_City', type:'cultura' },
]);

print('StaySky: colecciones + índices + 10 ciudades cargadas');