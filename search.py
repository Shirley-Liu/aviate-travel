import csv, json, os, math, re, html
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse, parse_qs
ROOT = Path('/aviation')
AIRLINE_FIELDS = ['Airline ID','Name','Alias','IATA','ICAO','Callsign','Country','Active']
AIRPORT_FIELDS = ['Airport ID','Name','City','Country','IATA','ICAO','Latitude','Longitude','Altitude (feet)','UTC offset','DST','Time zone','Type','Source']
class AviationDatabase:
    def __init__(self):
        self.airlines = self.load('SB-airlines.txt', AIRLINE_FIELDS)
        self.airports = self.load('SB-airports.txt', AIRPORT_FIELDS)
        with (ROOT/'data'/'SB-routes.txt').open(encoding='utf-8-sig', newline='') as f:
            self.routes = list(csv.reader(f))
        self.airport_connectivity = Counter()
        for route in self.routes:
            for airport_id in set((route[3],route[5])): self.airport_connectivity[airport_id] += 1
        self.nonstop_out = {}
        self.nonstop_in = {}
        for route in self.routes:
            if route[7]=='0':
                self.nonstop_out.setdefault(route[3],{}).setdefault(route[5],[]).append(route)
                self.nonstop_in.setdefault(route[5],{}).setdefault(route[3],[]).append(route)
        self.airline_ids = {a['Airline ID']:a for a in self.airlines}
        self.airport_ids = {a['Airport ID']:a for a in self.airports}
    def load(self, name, fields):
        with (ROOT/'data'/name).open(encoding='utf-8-sig', newline='') as f:
            return [dict(zip(fields, [None if x == '\\N' else x for x in row])) for row in csv.reader(f) if row]
    @staticmethod
    def distance(a, b):
        lat1, lon1, lat2, lon2 = map(math.radians, map(float, (a['Latitude'],a['Longitude'],b['Latitude'],b['Longitude'])))
        h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
        return 3958.7613 * 2 * math.asin(math.sqrt(min(1,max(0,h))))
    def one_hop(self, source, destination):
        source, destination = source.strip().upper(), destination.strip().upper()
        airports = {a['IATA']:a for a in self.airports if a['IATA']}
        empty = {'title':'One-connection trips','rows':[], 'cities':[]}
        if source not in airports or destination not in airports:
            return dict(empty, note='Enter valid source and destination airport IATA codes in this dataset.')
        if source == destination:
            return dict(empty, note='Choose two different airports.')
        s, d = airports[source], airports[destination]
        # Exactly one transfer: three distinct airports; no recursive graph walk.
        first = self.nonstop_out.get(s['Airport ID'],{})
        second = self.nonstop_in.get(d['Airport ID'],{})
        baseline = self.distance(s,d)
        candidates, cities = [], {}
        total_pairs = 0
        for airport_id in first.keys() & second.keys():
            if airport_id in {s['Airport ID'],d['Airport ID']}:
                continue
            x = self.airport_ids.get(airport_id)
            if not x:
                continue
            # Geometry is evaluated once per intermediate, never per airline pair.
            leg1,leg2 = self.distance(s,x),self.distance(x,d)
            pair_count = len(first[airport_id])*len(second[airport_id])
            total_pairs += pair_count
            candidates.append((leg1+leg2,x['IATA'] or '',airport_id,leg1,leg2))
            city=cities.setdefault((x['City'],x['Country']),{'city':x['City'],'country':x['Country'],'lat':float(x['Latitude']),'lon':float(x['Longitude']),'pairs':0,'airports':[]})
            city['pairs']+=pair_count
            city['airports'].append(x['IATA'])
        rows=[]
        for total,_,airport_id,leg1,leg2 in sorted(candidates):
            x=self.airport_ids[airport_id]
            for r1 in sorted(first[airport_id],key=lambda r:(self.airline_ids.get(r[1],{}).get('Name',r[0]),tuple(r))):
                for r2 in sorted(second[airport_id],key=lambda r:(self.airline_ids.get(r[1],{}).get('Name',r[0]),tuple(r))):
                    airline1,airline2=self.airline_ids.get(r1[1],{}),self.airline_ids.get(r2[1],{})
                    row={'Source':source,'Via':x['IATA'],'Intermediate city':x['City'],'Destination':destination,'First airline':airline1.get('Name',r1[0]),'Second airline':airline2.get('Name',r2[0]),'First leg miles':leg1,'Second leg miles':leg2,'Total miles':total,'Direct distance miles':baseline,'Extra distance miles':max(0,total-baseline),'Detour factor':total/baseline if baseline else 1,'Transfer route records':self.airport_connectivity[airport_id]}
                    for label,entity in [('Source airport',s),('Intermediate airport',x),('Destination airport',d),('First airline',airline1),('Second airline',airline2)]:
                        row.update({label+' / '+k:v for k,v in entity.items()})
                    rows.append(row)
        top=sorted(cities.values(),key=lambda c:(-c['pairs'],c['city'],c['country']))[:5]
        return {'title':source+' to '+destination+' with one connection','rows':rows,'cities':top,'totalMatches':total_pairs,'note':f'All {total_pairs} route pairs are available, ordered by total distance. Filters and CSV apply to all matching routes. City ranking counts all matching pairs. Both legs have 0 stops. Great-circle distances do not establish schedule or ticket compatibility.'}
    def nonstop(self, source, destination):
        source, destination = source.strip().upper(), destination.strip().upper()
        airports = {a['IATA']:a for a in self.airports if a['IATA']}
        result = {'title':source+' to '+destination+' non-stop','rows':[], 'cities':[]}
        if source not in airports or destination not in airports:
            return dict(result, note='Enter valid source and destination airport IATA codes in this dataset.')
        if source == destination:
            return dict(result, note='Choose two different airports.')
        s,d = airports[source],airports[destination]
        distance = round(self.distance(s,d),1)
        for r in self.routes:
            if r[3] == s['Airport ID'] and r[5] == d['Airport ID'] and r[7] == '0':
                airline = self.airline_ids.get(r[1],{})
                row = {'Source':source,'Destination':destination,'First airline':airline.get('Name',r[0]),'Total miles':distance,'Stops':0,'Codeshare':r[6] or None,'Aircraft codes':r[8]}
                for label,entity in [('Source airport',s),('Destination airport',d),('Airline',airline)]:
                    row.update({label+' / '+k:v for k,v in entity.items()})
                result['rows'].append(row)
        result['rows'].sort(key=lambda r:r['First airline'])
        result['note'] = 'Non-stop route records (Stops = 0). Distances are great-circle air miles.'
        return result
    def flights(self, source, destination, trip='one_way', stops='one_stop'):
        if trip not in ('one_way','round_trip') or stops not in ('nonstop','one_stop'):
            return {'title':'Invalid flight search','rows':[], 'note':'Choose a valid trip type and stops option.'}
        search = self.nonstop if stops == 'nonstop' else self.one_hop
        outbound = search(source,destination)
        sections = [{'label':'Outbound','rows':outbound['rows']}]
        notes = [outbound.get('note','')]
        if trip == 'round_trip':
            inbound = search(destination,source)
            sections.append({'label':'Return','rows':inbound['rows']})
            if not inbound['rows']:
                notes.append('No matching return routes were found.')
            notes.append('Outbound and return options are shown separately; choose one in each direction. The stops filter applies to each direction.')
        notes.append('This dataset has no travel dates, schedules, fares, or ticket availability.')
        return {'title':source.strip().upper()+(' ↔ ' if trip == 'round_trip' else ' → ')+destination.strip().upper(), 'rows':outbound['rows'], 'sections':sections, 'cities':outbound.get('cities',[]), 'note':' '.join(notes)}
    def query(self, mode, code):
        code = code.strip().upper()
        if mode == 'identity':
            return {'title':'Site owner', 'rows':[{'Name':os.getenv('AVIATION_STUDENT_NAME','Xiaolin Liu')}], 'note':'Site ownership information.'}
        kind = 'airline' if mode in ('airline','airline_routes','airlines') else 'airport'
        entities = self.airlines if kind == 'airline' else self.airports
        if mode in ('airlines','airports'):
            result = {'title':'All '+mode, 'rows':sorted(entities, key=lambda a:a['IATA'] or '')}
            if mode == 'airports':
                result['reportMap'] = {'directory':True, 'center':None, 'points':[{'code':airport['IATA'],'name':airport['Name'],'city':airport['City'],'lat':float(airport['Latitude']),'lon':float(airport['Longitude']),'count':1} for airport in result['rows']]}
            return result
        selected = next((a for a in entities if a['IATA'] == code), None)
        if not selected:
            return {'title':'No matching '+kind, 'rows':[], 'note':'Check the IATA code. This assignment dataset contains a limited selection.'}
        if mode in ('airline','airport'):
            return {'title':selected['Name'], 'rows':[selected]}
        counts = Counter()
        if mode == 'airline_routes':
            for r in self.routes:
                if r[1] == selected['Airline ID']:
                    for airport_id in set((r[3],r[5])):
                        counts[airport_id] += 1
            lookup = self.airport_ids
        else:
            for r in self.routes:
                if selected['Airport ID'] in (r[3],r[5]):
                    counts[r[1]] += 1
            lookup = self.airline_ids
        rows = [dict(lookup[k], **{'# routes':v}) for k,v in counts.items() if k in lookup]
        rows.sort(key=lambda a:(-a['# routes'],a['IATA'] or ''))
        airport_counts = Counter()
        center = None
        if mode == 'airline_routes':
            airport_counts = counts
        else:
            center = selected
            for r in self.routes:
                if selected['Airport ID'] in (r[3],r[5]):
                    other = r[5] if r[3] == selected['Airport ID'] else r[3]
                    airport_counts[other] += 1
        points = []
        for airport_id, count in airport_counts.items():
            airport = self.airport_ids.get(airport_id)
            if airport:
                points.append({'code':airport['IATA'], 'name':airport['Name'], 'city':airport['City'], 'lat':float(airport['Latitude']), 'lon':float(airport['Longitude']), 'count':count})
        points.sort(key=lambda point:(-point['count'], point['code'] or ''))
        focus = {'code':center['IATA'],'name':center['Name'],'lat':float(center['Latitude']),'lon':float(center['Longitude'])} if center else None
        return {'title':selected['Name']+' - routes to/from', 'rows':rows, 'reportMap':{'points':points,'center':focus}, 'note':'Counts include incoming and outgoing route records; each entity appears once.'}

DB = AviationDatabase()
def search_json(payload):
    q = json.loads(payload)
    mode = q.get('mode', 'airline')
    code = q.get('code', '')
    destination = q.get('destination', '')
    if mode == 'flights':
        result = DB.flights(code, destination, q.get('trip', 'one_way'), q.get('stops', 'one_stop'))
    elif mode == 'one_hop':
        result = DB.one_hop(code, destination)
    elif mode in ('airline','airport','airline_routes','airport_routes','airlines','airports','identity'):
        result = DB.query(mode, code)
    else:
        raise ValueError('Unknown search mode')
    return json.dumps(result)
