def basicFN_mockup(tx):
    # Create a basic temporal schema with a few nodes and relationships
    # This is a simple example for initial testing.
    query = """
CREATE (s1:Source {
  id: 'src-001', 
  type: 'video', 
  title: 'Why Is Russia Not Rich', 
  url: 'https://youtu.be/IoZ6dBCgk1M'
}),
(ec1:Event:Chapter {
  id: 'chapter-001',
  type: 'chapter',
  title: 'Early Russia',
  description: 'Serfdom and the Commune',
  category: 'Chapter',
  chapter_number: 1
}),
(tsc1:Timestamp {
  id: 'ts-ch1-range',
  type: 'range',
  value: '1547/1800',
  start: '1547',
  end: '1800',
  precision: 'year',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ec1)-[:FOLLOWED_FROM]->(s1),
(ec1)-[:OCCURRED_DURING]->(tsc1),
(ec2:Event:Chapter {
  id: 'chapter-002',
  type: 'chapter',
  title: 'Imperial Russia',
  description: 'Bad Geography',
  category: 'Chapter',
  chapter_number: 2
}),
(tsc2:Timestamp {
  id: 'ts-ch2-range',
  type: 'range',
  value: '1800/1861',
  start: '1800',
  end: '1861',
  precision: 'year',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ec2)-[:FOLLOWED_FROM]->(s1),
(ec2)-[:OCCURRED_DURING]->(tsc2),
(ec3:Event:Chapter {
  id: 'chapter-003',
  type: 'chapter',
  title: 'Laissez-faire Russia',
  description: 'The Failure of the Aristocracy',
  category: 'Chapter',
  chapter_number: 3
}),
(tsc3:Timestamp {
  id: 'ts-ch3-range',
  type: 'range',
  value: '1861/1891',
  start: '1861',
  end: '1891',
  precision: 'year',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ec3)-[:FOLLOWED_FROM]->(s1),
(ec3)-[:OCCURRED_DURING]->(tsc3),
(ec4:Event:Chapter {
  id: 'chapter-004',
  type: 'chapter',
  title: 'Industrial Russia',
  description: 'The Failure of the Aristocracy',
  category: 'Chapter',
  chapter_number: 4
}),
(tsc4:Timestamp {
  id: 'ts-ch4-range',
  type: 'range',
  value: '1891/1913',
  start: '1891',
  end: '1913',
  precision: 'year',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ec4)-[:FOLLOWED_FROM]->(s1),
(ec4)-[:OCCURRED_DURING]->(tsc4),
(ec5:Event:Chapter {
  id: 'chapter-005',
  type: 'chapter',
  title: 'Communist Russia',
  description: 'The Communist Revolution',
  category: 'Chapter',
  chapter_number: 5
}),
(tsc5:Timestamp {
  id: 'ts-ch5-range',
  type: 'range',
  value: '1917/1928',
  start: '1917',
  end: '1928',
  precision: 'year',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ec5)-[:FOLLOWED_FROM]->(s1),
(ec5)-[:OCCURRED_DURING]->(tsc5),
(ec6:Event:Chapter {
  id: 'chapter-006',
  type: 'chapter',
  title: "Stalin's Russia",
  description: 'A command Economy',
  category: 'Chapter',
  chapter_number: 6
}),
(tsc6:Timestamp {
  id: 'ts-ch6-range',
  type: 'range',
  value: '1928/1945',
  start: '1928',
  end: '1945',
  precision: 'year',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ec6)-[:FOLLOWED_FROM]->(s1),
(ec6)-[:OCCURRED_DURING]->(tsc6),
(ec7:Event:Chapter {
  id: 'chapter-007',
  type: 'chapter',
  title: 'Cold War Russia',
  description: 'The Slow Slowdown',
  category: 'Chapter',
  chapter_number: 7
}),
(tsc7:Timestamp {
  id: 'ts-ch7-range',
  type: 'range',
  value: '1945/1985',
  start: '1945',
  end: '1985',
  precision: 'year',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ec7)-[:FOLLOWED_FROM]->(s1),
(ec7)-[:OCCURRED_DURING]->(tsc7),
(ec8:Event:Chapter {
  id: 'chapter-008',
  type: 'chapter',
  title: 'Declining Russia',
  description: 'Breakup of the USSR',
  category: 'Chapter',
  chapter_number: 8
}),
(tsc8:Timestamp {
  id: 'ts-ch8-range',
  type: 'range',
  value: '1985/1991',
  start: '1985',
  end: '1991',
  precision: 'year',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ec8)-[:FOLLOWED_FROM]->(s1),
(ec8)-[:OCCURRED_DURING]->(tsc8),
(ec9:Event:Chapter {
  id: 'chapter-009',
  type: 'chapter',
  title: 'Capitalist Russia',
  description: 'The Oligarchy',
  category: 'Chapter',
  chapter_number: 9
}),
(tsc9:Timestamp {
  id: 'ts-ch9-range',
  type: 'range',
  value: '1991/1999',
  start: '1991',
  end: '1999',
  precision: 'year',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ec9)-[:FOLLOWED_FROM]->(s1),
(ec9)-[:OCCURRED_DURING]->(tsc9),
(ec10:Event:Chapter {
  id: 'chapter-010',
  type: 'chapter',
  title: "Putin's Russia",
  description: 'Industrial Feudalism',
  category: 'Chapter',
  chapter_number: 10
}),
(tsc10:Timestamp {
  id: 'ts-ch10-range',
  type: 'range',
  value: '1999/2020',
  start: '1999',
  end: '2020',
  precision: 'year',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ec10)-[:FOLLOWED_FROM]->(s1),
(ec10)-[:OCCURRED_DURING]->(tsc10)
"""
    result = tx.run(query)
    query = """ 
MATCH (s1:Source {id: 'src-001'})
CREATE (er1:Event {
  id: "1", 
  type: 'policy-change',
  title: "Emancipation [of serfs] Reform",
  location: "Russia",
  description: 'The Failure of the Aristocracy',
  category: 'Policy Change'
}),
(t1:Timestamp {value: "1861", precision: "year"}),
(er1)-[:FOLLOWED_FROM]->(s1),
(er1)-[:OCCURRED_AT]->(t1),
(er2:Event {
  id: "2", 
  type: 'crisis',
  title: "February revolution",
  location: "Russia",
  description: 'The Communist Revolution',
  category: 'Revolution'
}),
(t2:Timestamp {value: "1917-02", precision: "month"}),
(er2)-[:FOLLOWED_FROM]->(s1),
(er2)-[:OCCURRED_AT]->(t2),
(er3:Event {
  id: "3", 
  type: 'crisis',
  title: "November Revolution",
  location: "Russia",
  description: 'Bolshevik Revolution',
  category: 'Revolution'
}),
(t3:Timestamp {value: "1917-11", precision: "month"}),
(er3)-[:FOLLOWED_FROM]->(s1),
(er3)-[:OCCURRED_AT]->(t3),
(er4:Event {
  id: "4", 
  type: 'country-change',
  title: "Soviet Dissolution",
  location: "Russia",
  description: 'Dissolution of the Soviet Union',
  category: 'Dissolution'
}),
(t4:Timestamp {value: "1991-12-26", precision: "date"}),
(er4)-[:FOLLOWED_FROM]->(s1),
(er4)-[:OCCURRED_AT]->(t4),
(ew5:Event {
  id: "5", 
  type: 'war',
  title: "World War I",
  location: "World",
  description: 'First World war',
  category: 'World War'
}),
(tw5:Timestamp {
  id: 'ts-ew5-range',
  type: 'range',
  value: '1914/1917',
  start: '1914',
  end: '1917',
  precision: 'year',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ew5)-[:FOLLOWED_FROM]->(s1),
(ew5)-[:OCCURRED_DURING]->(tw5),
(ew6:Event {
  id: "6", 
  type: 'crisis',
  title: "Great Depression",
  location: "World",
  description: 'Great Depression of the Industrialized Nations',
  category: 'Economic'
}),
(tw6:Timestamp {
  id: 'ts-ew6-range',
  type: 'range',
  value: '1929/1939',
  start: '1929',
  end: '1939',
  precision: 'year',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ew6)-[:FOLLOWED_FROM]->(s1),
(ew6)-[:OCCURRED_DURING]->(tw6),
(ew7:Event {
  id: "7", 
  type: 'War',
  title: "World War II",
  location: "World",
  description: 'Second World War',
  category: 'World War'
}),
(tw7:Timestamp {
  id: 'ts-ew7-range',
  type: 'range',
  value: '1939/1945',
  start: '1939',
  end: '1945',
  precision: 'year',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ew7)-[:FOLLOWED_FROM]->(s1),
(ew7)-[:OCCURRED_DURING]->(tw7),
(ew8:Event {
  id: "8", 
  type: 'crisis',
  title: "First Atomic Bomb",
  location: "Japan",
  description: 'Bomb dropped on Hiroshima',
  category: 'bombing'
}),
(tw8:Timestamp {
  id: 'ts-ew8-time',
  type: 'yyyy-mm-dd hh:mm',
  value: '1945-08-06T08:15',
  precision: 'minute',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ew8)-[:FOLLOWED_FROM]->(s1),
(ew8)-[:OCCURRED_AT]->(tw8),
(ew9:Event {
  id: "9", 
  type: 'crisis',
  title: "Second Atomic Bomb",
  location: "Japan",
  description: 'Bomb dropped on Nagasaki',
  category: 'bombing'
}),
(tw9:Timestamp {
  id: 'ts-ew9-time',
  type: 'yyyy-mm-ddThh:mm',
  value: '1945-08-09T11:00',
  precision: 'minute',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ew9)-[:FOLLOWED_FROM]->(s1),
(ew9)-[:OCCURRED_AT]->(tw9),
(ew10:Event {
  id: "10", 
  type: 'war',
  title: "Afgan war",
  location: "Afghanistan",
  description: 'Afgan Soviet War',
  category: 'bombing'
}),
(tw10:Timestamp {
  id: 'ts-ew10-range',
  type: 'range',
  value: '1979/1989',
  start: '1979-12-24',
  end: '1989-02-15', 
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(ew10)-[:FOLLOWED_FROM]->(s1),
(ew10)-[:OCCURRED_DURING]->(tw10)
"""
    tx.run(query)
    query = """
MATCH (s1:Source {id: 'src-001'})
CREATE (eu1:Event {
  id: "eu-001", 
  type: 'crisis',
  title: "Pearl Harbor",
  location: "Hawaii",
  description: 'Attack on Pearl Harbor',
  category: 'bombing'
}),
(tu1:Timestamp {
  id: 'ts-eu1-date',
  type: 'yyyy-mm-dd',
  value: '1941-12-07',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(eu1)-[:FOLLOWED_FROM]->(s1),
(eu1)-[:OCCURRED_AT]->(tu1),
(g:Event:Group {
  id: "group1", 
  type: 'enum-events',
  title: "Sovereignty from Russia",
  description: 'These countries seceded from the Soviet Union in rapid succession',
  category: 'Sovereignty'
}),
(g)-[:FOLLOWED_FROM]->(s1),
(sov1:Event:Sovereignty {
  id: "sov-001",
  type: 'sovereign-state',
  title: "Succession of Lithuania"
}),
(tsov1:Timestamp {
  id: 'ts-sov1-date',
  type: 'yyyy-mm-dd',
  value: '1990-03-11',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(sov1)-[:FOLLOWED_FROM]->(g),
(sov1)-[:OCCURRED_AT]->(tsov1),
(sov2:Event:Sovereignty {
  id: "sov-002",
  type: 'sovereign-state',
  title: "Succession of Estonia"
}),
(tsov2:Timestamp {
  id: 'ts-sov2-date',
  type: 'yyyy-mm-dd',
  value: '1991-08-20',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(sov2)-[:FOLLOWED_FROM]->(g),
(sov2)-[:OCCURRED_AT]->(tsov2),
(sov3:Event:Sovereignty {
  id: "sov-003",
  type: 'sovereign-state',
  title: "Succession of Latvia"
}),
(tsov3:Timestamp {
  id: 'ts-sov3-date',
  type: 'yyyy-mm-dd',
  value: '1991-08-21',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(sov3)-[:FOLLOWED_FROM]->(g),
(sov3)-[:OCCURRED_AT]->(tsov3),
(sov4:Event:Sovereignty {
  id: "sov-004",
  type: 'sovereign-state',
  title: "Succession of Ukraine"
}),
(tsov4:Timestamp {
  id: 'ts-sov4-date',
  type: 'yyyy-mm-dd',
  value: '1991-08-24',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(sov4)-[:FOLLOWED_FROM]->(g),
(sov4)-[:OCCURRED_AT]->(tsov4),
(sov5:Event:Sovereignty {
  id: "sov-005",
  type: 'sovereign-state',
  title: "Succession of Belarus"
}),
(tsov5:Timestamp {
  id: 'ts-sov5-date',
  type: 'yyyy-mm-dd',
  value: '1991-08-25',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(sov5)-[:FOLLOWED_FROM]->(g),
(sov5)-[:OCCURRED_AT]->(tsov5),
(sov6:Event:Sovereignty {
  id: "sov-006",
  type: 'sovereign-state',
  title: "Succession of Moldova"
}),
(tsov6:Timestamp {
  id: 'ts-sov6-date',
  type: 'yyyy-mm-dd',
  value: '1991-08-27',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(sov6)-[:FOLLOWED_FROM]->(g),
(sov6)-[:OCCURRED_AT]->(tsov6),
(sov7:Event:Sovereignty {
  id: "sov-007",
  type: 'sovereign-state',
  title: "Succession of Uzbekistan"
}),
(tsov7:Timestamp {
  id: 'ts-sov7-date',
  type: 'yyyy-mm-dd',
  value: '1991-08-31',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(sov7)-[:FOLLOWED_FROM]->(g),
(sov7)-[:OCCURRED_AT]->(tsov7),
(sov8:Event:Sovereignty {
  id: "sov-008",
  type: 'sovereign-state',
  title: "Succession of Kyrgyzstan"
}),
(tsov8:Timestamp {
  id: 'ts-sov8-date',
  type: 'yyyy-mm-dd',
  value: '1991-08-31',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(sov8)-[:FOLLOWED_FROM]->(g),
(sov8)-[:OCCURRED_AT]->(tsov8),
(sov9:Event:Sovereignty {
  id: "sov-009",
  type: 'sovereign-state',
  title: "Succession of Tajikistan"
}),
(tsov9:Timestamp {
  id: 'ts-sov9-date',
  type: 'yyyy-mm-dd',
  value: '1991-09-09',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(sov9)-[:FOLLOWED_FROM]->(g),
(sov9)-[:OCCURRED_AT]->(tsov9),
(sov10:Event:Sovereignty {
  id: "sov-010",
  type: 'sovereign-state',
  title: "Succession of Armenia"
}),
(tsov10:Timestamp {
  id: 'ts-sov10-date',
  type: 'yyyy-mm-dd',
  value: '1991-09-21',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(sov10)-[:FOLLOWED_FROM]->(g),
(sov10)-[:OCCURRED_AT]->(tsov10),
(sov11:Event:Sovereignty {
  id: "sov-011",
  type: 'sovereign-state',
  title: "Succession of Azerbaijan"
}),
(tsov11:Timestamp {
  id: 'ts-sov11-date',
  type: 'yyyy-mm-dd',
  value: '1991-10-18',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(sov11)-[:FOLLOWED_FROM]->(g),
(sov11)-[:OCCURRED_AT]->(tsov11),
(sov12:Event:Sovereignty {
  id: "sov-012",
  type: 'sovereign-state',
  title: "Succession of Turkmenistan"
}),
(tsov12:Timestamp {
  id: 'ts-sov12-date',
  type: 'yyyy-mm-dd',
  value: '1991-10-27',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(sov12)-[:FOLLOWED_FROM]->(g),
(sov12)-[:OCCURRED_AT]->(tsov12),
(sov13:Event:Sovereignty {
  id: "sov-013",
  type: 'sovereign-state',
  title: "Succession of Kazakhstan"
}),
(tsov13:Timestamp {
  id: 'ts-sov13-date',
  type: 'yyyy-mm-dd',
  value: '1991-12-16',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(sov13)-[:FOLLOWED_FROM]->(g),
(sov13)-[:OCCURRED_AT]->(tsov13),
(sov14:Event:Sovereignty {
  id: "sov-014",
  type: 'sovereign-state',
  title: "Succession of Turkmenistan"
}),
(tsov14:Timestamp {
  id: 'ts-sov14-date',
  type: 'yyyy-mm-dd',
  value: '1991-10-27',
  precision: 'day',
  certainty: 'confirmed',
  calendar: 'gregorian'
}),
(sov14)-[:FOLLOWED_FROM]->(g),
(sov14)-[:OCCURRED_AT]->(tsov14)
"""
    tx.run(query)


def basicMFN_mockup(tx):           
    # mockup data for testing the chapter schema
    # Create timeline node, chapter nodes and event range nodes. Link the chapters together and everything to their ranges.
    create_nodes_query = """
    CREATE (tl:Timeline {brief: "Russian Economic Development", source: "video", dates: "1547-2020"}), 
        (tlover:YrRange {desc: "1547-2020", yearS: 1547, yearE: 2020}),
        (c1:Chapter {title: "Early Russia", subTitle: "Serfdom and the Commune", seqNo: 1}),
        (c1r:YrRange {desc: "1547-1800", yearS: 1547, yearE: 1800}),
        (c2:Chapter {title: "Imperial Russia", subTitle:"Bad Geography", seqNo: 2}),
        (c2r:YrRange {desc: "1800-1861", yearS: 1800, yearE: 1861}),
        (c3:Chapter {title: "Laissez-faire Russian", subTitle: "The Failure of the Aristocracy", seqNo: 3}),
        (c3r:YrRange {desc: "1861-1891", yearS: 1861, yearE: 1891}),
        (c4:Chapter {title: "Industrial Russia", subTitle: "The Failure of the Aristocracy", seqNo: 4}),
        (c4r:YrRange {desc: "1891-1913", yearS: 1891, yearE: 1913}),
        (c5:Chapter {title: "Communist Russia", subTitle: "The Communist Revolution", seqNo: 5}),
        (c5r:YrRange {desc: "1917-1928", yearS: 1917, yearE: 1928}),
        (c6:Chapter {title: "Stalin's Russia", subTitle: "A command Economy", seqNo: 6}),
        (c6r:YrRange {desc: "1928-1945", yearS: 1928, yearE: 1945}),
        (c7:Chapter {title: "Cold War Russia", subTitle: "The Slow Slowdown", seqNo: 7}),
        (c7r:YrRange {desc: "1945-1985", yearS: 1945, yearE: 1985}),
        (c8:Chapter {title: "Declining Russia", subTitle: "Breakup of the USSR", seqNo: 8}),
        (c8r:YrRange {desc: "1985-1991", yearS: 1985, yearE: 1991}),
        (c9:Chapter {title: "Capitalist Russia", subTitle: "The Oligarchy", seqNo: 9}),
        (c9r:YrRange {desc: "1991-1999", yearS: 1991, yearE: 1999}),
        (c10:Chapter {title: "Putin's Russia", subTitle: "Industrial Feudalism", seqNo: 10}),
        (c10r:YrRange {desc: "1999-2020", yearS: 1999, yearE: 2020}),
        (tl)-[tlrange:Span {scope: "full"}]->(tlover),
        (tl)-[:Chapter]->(c1),
        (c1)-[:Span]->(c1r),
        (c2)-[:Span]->(c2r),
        (c3)-[:Span]->(c3r),
        (c4)-[:Span]->(c4r),
        (c5)-[:Span]->(c5r),
        (c6)-[:Span]->(c6r),
        (c7)-[:Span]->(c7r),
        (c8)-[:Span]->(c8r),
        (c9)-[:Span]->(c9r),
        (c10)-[:Span]->(c10r),
        (c1)-[:Next]->(c2),
        (c2)-[:Next]->(c3),
        (c3)-[:Next]->(c4),
        (c4)-[:Next]->(c5),
        (c5)-[:Next]->(c6),
        (c6)-[:Next]->(c7),
        (c7)-[:Next]->(c8),
        (c8)-[:Next]->(c9),
        (c9)-[:Next]->(c10)
        return tlover
    """
    result = tx.run(create_nodes_query)
    
    # Create Sovereignty events relationship
    create_sovereign_query = """
    MATCH (tl:Timeline {brief:"Russian Economic Development"})
    CREATE (ss:EventGroup {title: "Secede", desc: "States that Seceded from the Russian union"}),
        (tl)-[:Event]->(ss),
        (s1:Sovereignty {state:"Lithuania", year: 1990}),
        (s2:Sovereignty {state: "Georgia", year: 1991}),
        (s3:Sovereignty {state: "Estonia", year: 1991}),
        (s4:Sovereignty {state: "Latvia", year: 1991}),
        (s5:Sovereignty {state: "Ukraine", year: 1991}),
        (s6:Sovereignty {state: "Belarus", year: 1991}),
        (s7:Sovereignty {state: "Moldova", year: 1991}),
        (s8:Sovereignty {state: "Uzbekistan", year: 1991}),
        (s9:Sovereignty {state: "Kyrgyzstan", year: 1991}),
        (s10:Sovereignty {state: "Tajikistan", year: 1991}),
        (s11:Sovereignty {state: "Armenia", year: 1991}),
        (s12:Sovereignty {state: "Azerbaijan", year: 1991}),
        (s13:Sovereignty {state: "Turkmenistan", year: 1991}),
        (s14:Sovereignty {state: "Kazakhstan", year: 1991}),
        (cd1:CalendarDate {desc: "March 11, 1990", year: 1990, month: "March", nMonth: 2, day: 11}),
        (cd2:CalendarDate {desc: "April 9, 1991", year: 1991, month: "April", nMonth: 3, day: 9}),
        (cd3:CalendarDate {desc: "August 20, 1991", year: 1991, month: "August", nMonth: 7, day: 20}),
        (cd4:CalendarDate {desc: "August 21, 1991", year: 1991, month: "August", nMonth: 7, day: 21}),
        (cd5:CalendarDate {desc: "August 24, 1991", year: 1991, month: "August", nMonth: 7, day: 24}),
        (cd6:CalendarDate {desc: "August 25, 1991", year: 1991, month: "August", nMonth: 7, day: 25}),
        (cd7:CalendarDate {desc: "August 27, 1991", year: 1991, month: "August", nMonth: 7, day: 27}),
        (cd8:CalendarDate {desc: "August 31, 1991", year: 1991, month: "August", nMonth: 7, day: 31}),
        (cd9:CalendarDate {desc: "August 31, 1991", year: 1991, month: "August", nMonth: 7, day: 31}),
        (cd10:CalendarDate {desc: "September 9, 1991", year: 1991, month: "September", nMonth: 8, day: 9}),
        (cd11:CalendarDate {desc: "September 21, 1991", year: 1991, month: "September", nMonth: 8, day: 21}),
        (cd12:CalendarDate {desc: "October 18, 1991", year: 1991, month: "October", nMonth: 9, day: 18}),
        (cd13:CalendarDate {desc: "October 27, 1991", year: 1991, month: "October", nMonth: 9, day: 27}),
        (cd14:CalendarDate {desc: "December 16, 1991", year: 1991, month: "December", nMonth: 11, day: 16}),
        (s1)-[:Suceded]->(cd1),
        (s2)-[:Suceded]->(cd2),
        (s3)-[:Suceded]->(cd3),
        (s4)-[:Suceded]->(cd4),
        (s5)-[:Suceded]->(cd5),
        (s6)-[:Suceded]->(cd6),
        (s7)-[:Suceded]->(cd7),
        (s8)-[:Suceded]->(cd8),
        (s9)-[:Suceded]->(cd9),
        (s10)-[:Suceded]->(cd10),
        (s11)-[:Suceded]->(cd11),
        (s12)-[:Suceded]->(cd12),
        (s13)-[:Suceded]->(cd13),
        (s14)-[:Suceded]->(cd14),
        (ss)-[:Sucede]->(s1),
        (ss)-[:Sucede]->(s2),
        (ss)-[:Sucede]->(s3),
        (ss)-[:Sucede]->(s4),
        (ss)-[:Sucede]->(s5),
        (ss)-[:Sucede]->(s6),
        (ss)-[:Sucede]->(s7),
        (ss)-[:Sucede]->(s8),
        (ss)-[:Sucede]->(s9),
        (ss)-[:Sucede]->(s10),
        (ss)-[:Sucede]->(s11),
        (ss)-[:Sucede]->(s12),
        (ss)-[:Sucede]->(s13),
        (ss)-[:Sucede]->(s14)
        RETURN tl
    """
    result = tx.run(create_sovereign_query)
    create_stat_query = """
        MATCH (tl:Timeline {brief:"Russian Economic Development"})
        CREATE (d1:Statistic {title: "Urban vs Rural", desc: 'Percent of people in towns/cities vs rural', unit: '%', percent: 12.8 }),
            (tl)-[:Event]->(d1),
            (d1)-[:Event]->(:Year {year: 1800}) return tl
        """
    result = tx.run(create_stat_query)

    create_russia_event_query = """
        MATCH (tl:Timeline {brief:"Russian Economic Development"})
        CREATE (reg:EventGroup {title: "Russian Events", desc: "Events that impacted Russian Economic Development"}),
            (tl)-[:Event]->(reg),    
            (reg)-[:Event]->(e1:Event {title: "Emancipation Reform", desc: "Emancipation of serfs Reform"}),
            (e1)-[:Year]->(:Year {year: 1861}),
            (reg)-[:Event]->(e2:Event {title: "February Revolution"}),
            (e2)-[:Year]->(:MonYear {year: 1917, month: 'March', nMonth: 2}),
            (reg)-[:Event]->(e3:Event {title:'Bolshevik Revolution'}),
            (e3)-[:Year]->(:MonYear {year: 1917, month: 'November', nMonth: 10}),
            (reg)-[:Event]->(e4:Event {title: "Soviet Dissolution", desc: 'dissolution of the Soviet Union'}),
            (e4)-[:Year]->(:CalendarDate {desc: 'Dec 26, 1991', year: 1991, month: 'Dec', nMonth: 11, day: 26})
            RETURN tl
        """
    result = tx.run(create_russia_event_query)
    create_world_event_query = """
        MATCH (tl:Timeline {brief:"Russian Economic Development"})
        CREATE (weg:EventGroup {title: "World Events", desc: "World Events for context for Russian Economic Development"}),
            (tl)-[:Event]->(weg),
            (weg)-[:Event]->(w1:Event {title: "First World War"}),
            (w1)-[:YrRange]->(:YrRange {desc: '1914-1917', year1: 1914, year2: 1917}),
            (weg)-[:Event]->(w2:Event {title: 'Great Depression', desc: 'The Dirty Thirties'}),
            (w2)-[:YrRange]->(:YrRange {desc: '1929-1939', year1: 1929, year2: 1939}),
            (weg)-[:Event]->(w3:Event {title: 'World War II' }),
            (w3)-[:YrRange]->(:YrRange {desc: '1939-1945', year1: 1939, year2: 1945}),
            (weg)-[:Event]->(w4:Event {title: 'Hiroshima Bombed', desc: 'H-Bomb dropped on Hiroshima' }),
            (w4)-[:DateTime]->(:DateTime {desc: 'Aug. 6, 1945 at 8:15am', year: 1945, month: "Aug.", nMonth: 7, day: 6, hr: 8, min: 15}),
            (weg)-[:Event]->(w5:Event {title: 'Nagasaki Bombed', desc: 'H-Bomb dropped on Nagasaki' }),
            (w5)-[:DateTime]->(:DateTime {desc: 'Aug. 9, 1945 at 11:00am', year: 1945, month: "Aug.", nMonth: 7, day: 9, hr: 11, min: 0}),
            (weg)-[:Event]->(w6:Event {title: 'Afghan Soviet War' }),
            (w6)-[:Range]->(:CalendarRange {desc: 'Dec. 24, 1979-Feb 15, 1989', year1: 1979, year2: 1989, month1: "Dec.", nMonth1: 11, day1: 24, month2: "Feb.", nMonth2: 1, day2: 15}),
            (weg)-[:Event]->(w7:Event {title: 'Pearl Harbor', desc: 'Attack on Pearl Harbor' }),
            (w7)-[:Year]->(:CalendarDate {desc: 'December 7, 1941', year: 1941, month: 'December', nMonth: 11, day: 7})
            RETURN tl
        """
    result = tx.run(create_world_event_query)

    for record in result:
        print(record["tl"])
