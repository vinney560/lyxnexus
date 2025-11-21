
from flask import jsonify, request
import random
from datetime import datetime

# Mock data
MOCK_DATA = {
  "/api/user": {
    "id": 109,
    "username": "matasamantha",
    "mobile": "+1-359-278-0952x716",
    "is_admin": true,
    "status": true,
    "created_at": "2025-04-01T08:04:32.981317",
    "email": "pamela02@example.org"
  },
  "/api/announcements": [
    {
      "id": 330,
      "title": "Ever care.",
      "content": "**Important**: Professor him carry whether bar today. Or up beautiful listen ask card myself across.",
      "author": {
        "id": 74,
        "username": "fmcguire",
        "mobile": "+1-355-594-8086",
        "is_admin": false,
        "status": false,
        "created_at": "2025-03-11T19:51:03.025443",
        "email": "russobrandon@example.net"
      },
      "has_file": true,
      "file_type": "image/jpeg",
      "file_url": "/uploads/fall.jpeg",
      "file_name": "fall.jpeg",
      "created_at": "2025-11-07T19:39:51.590211",
      "is_pinned": false
    },
    {
      "id": 187,
      "title": "Simply find rise article join road week author determine.",
      "content": "**Important**: Effort window star. Agreement recently now level. Score go low. Ready community loss.\n\nCheck this link: http://www.oconnell-kemp.info/",
      "author": {
        "id": 914,
        "username": "ngarcia",
        "mobile": "001-277-366-1081x666",
        "is_admin": false,
        "status": true,
        "created_at": "2025-09-13T15:51:03.850986",
        "email": "martinezgloria@example.net"
      },
      "has_file": false,
      "file_type": null,
      "file_url": null,
      "file_name": null,
      "created_at": "2025-11-09T22:48:54.474465",
      "is_pinned": false
    },
    {
      "id": 433,
      "title": "Thought building could environmental senior dog such require run.",
      "content": "**Important**: Test decision get play trade military pretty. Shoulder member challenge world price agent professor fire. Institution big animal hear tend. Sing heart size build pull.",
      "author": {
        "id": 109,
        "username": "matasamantha",
        "mobile": "+1-359-278-0952x716",
        "is_admin": true,
        "status": true,
        "created_at": "2025-04-01T08:04:32.981317",
        "email": "pamela02@example.org"
      },
      "has_file": true,
      "file_type": "image/png",
      "file_url": "/uploads/watch.png",
      "file_name": "watch.png",
      "created_at": "2025-11-10T03:40:42.819489",
      "is_pinned": true
    },
    {
      "id": 78,
      "title": "Land three yourself second politics class.",
      "content": "**Important**: Social carry officer language medical lose. Effort decade charge provide always find to size. Himself civil his worker. Cover must decade administration. Establish every beautiful sort.\n\nCheck this link: https://www.roberts-reyes.com/",
      "author": {
        "id": 142,
        "username": "emily23",
        "mobile": "8078983332",
        "is_admin": false,
        "status": true,
        "created_at": "2025-10-31T19:19:37.647664",
        "email": "garrisonpatricia@example.org"
      },
      "has_file": true,
      "file_type": "application/pdf",
      "file_url": "/uploads/drug.pdf",
      "file_name": "drug.pdf",
      "created_at": "2025-11-04T08:31:49.010866",
      "is_pinned": false
    },
    {
      "id": 339,
      "title": "Yes course.",
      "content": "**Important**: Show challenge money partner mission coach quite. Eye just tell kitchen. Adult son hard my network establish live stock. Reflect resource wait him entire respond.",
      "author": {
        "id": 74,
        "username": "fmcguire",
        "mobile": "+1-355-594-8086",
        "is_admin": false,
        "status": false,
        "created_at": "2025-03-11T19:51:03.025443",
        "email": "russobrandon@example.net"
      },
      "has_file": true,
      "file_type": "text/plain",
      "file_url": "/uploads/cell.plain",
      "file_name": "cell.plain",
      "created_at": "2025-11-18T23:56:35.728645",
      "is_pinned": false
    },
    {
      "id": 414,
      "title": "You nothing.",
      "content": "**Important**: Place light against describe than free none. Take ahead place.",
      "author": {
        "id": 41,
        "username": "wbradley",
        "mobile": "(905)383-2477x4687",
        "is_admin": false,
        "status": true,
        "created_at": "2025-05-19T06:35:34.114598",
        "email": "riosdaniel@example.org"
      },
      "has_file": false,
      "file_type": null,
      "file_url": null,
      "file_name": null,
      "created_at": "2025-11-20T19:51:49.640187",
      "is_pinned": false
    },
    {
      "id": 236,
      "title": "Trip top old letter painting first score.",
      "content": "**Important**: Describe carry evidence. Instead ability yourself remain. Activity only couple experience specific thank.",
      "author": {
        "id": 451,
        "username": "jameshaney",
        "mobile": "583-289-8080",
        "is_admin": false,
        "status": true,
        "created_at": "2025-06-17T11:53:19.831993",
        "email": "brittany06@example.net"
      },
      "has_file": false,
      "file_type": null,
      "file_url": null,
      "file_name": null,
      "created_at": "2025-11-16T07:31:27.884307",
      "is_pinned": false
    },
    {
      "id": 186,
      "title": "Exist year in which themselves.",
      "content": "**Important**: Two peace yourself site marriage.",
      "author": {
        "id": 74,
        "username": "fmcguire",
        "mobile": "+1-355-594-8086",
        "is_admin": false,
        "status": false,
        "created_at": "2025-03-11T19:51:03.025443",
        "email": "russobrandon@example.net"
      },
      "has_file": true,
      "file_type": "image/jpeg",
      "file_url": "/uploads/who.jpeg",
      "file_name": "who.jpeg",
      "created_at": "2025-11-04T14:53:36.296178",
      "is_pinned": true
    },
    {
      "id": 214,
      "title": "Story create according blood without woman prove.",
      "content": "**Important**: Reality same life people table approach. Charge while behind truth recent. Candidate toward risk bit.\n\nCheck this link: https://www.franklin.com/",
      "author": {
        "id": 109,
        "username": "matasamantha",
        "mobile": "+1-359-278-0952x716",
        "is_admin": true,
        "status": true,
        "created_at": "2025-04-01T08:04:32.981317",
        "email": "pamela02@example.org"
      },
      "has_file": false,
      "file_type": null,
      "file_url": null,
      "file_name": null,
      "created_at": "2025-11-05T01:10:08.198457",
      "is_pinned": false
    },
    {
      "id": 37,
      "title": "Course fight along hold money.",
      "content": "Join issue part itself clear day. Hard ever difference house third step phone. Share building writer science another.",
      "author": {
        "id": 744,
        "username": "nicholselizabeth",
        "mobile": "+1-506-921-1997x6803",
        "is_admin": false,
        "status": true,
        "created_at": "2025-04-06T21:29:58.820408",
        "email": "hrodriguez@example.net"
      },
      "has_file": false,
      "file_type": null,
      "file_url": null,
      "file_name": null,
      "created_at": "2025-11-11T12:24:03.747212",
      "is_pinned": false
    },
    {
      "id": 242,
      "title": "Girl plan where provide land away hotel.",
      "content": "Above song idea program beyond ago argue. Message area edge.",
      "author": {
        "id": 142,
        "username": "emily23",
        "mobile": "8078983332",
        "is_admin": false,
        "status": true,
        "created_at": "2025-10-31T19:19:37.647664",
        "email": "garrisonpatricia@example.org"
      },
      "has_file": true,
      "file_type": "image/jpeg",
      "file_url": "/uploads/special.jpeg",
      "file_name": "special.jpeg",
      "created_at": "2025-11-17T17:28:50.234270",
      "is_pinned": false
    },
    {
      "id": 285,
      "title": "Believe soon western.",
      "content": "**Important**: Behind traditional sign shake down investment. Painting different how near.\n\nCheck this link: https://waters-bartlett.org/",
      "author": {
        "id": 74,
        "username": "fmcguire",
        "mobile": "+1-355-594-8086",
        "is_admin": false,
        "status": false,
        "created_at": "2025-03-11T19:51:03.025443",
        "email": "russobrandon@example.net"
      },
      "has_file": false,
      "file_type": null,
      "file_url": null,
      "file_name": null,
      "created_at": "2025-11-01T06:00:07.577099",
      "is_pinned": false
    },
    {
      "id": 268,
      "title": "Human show political.",
      "content": "Staff order business decision card hard. Population easy similar baby executive.",
      "author": {
        "id": 74,
        "username": "fmcguire",
        "mobile": "+1-355-594-8086",
        "is_admin": false,
        "status": false,
        "created_at": "2025-03-11T19:51:03.025443",
        "email": "russobrandon@example.net"
      },
      "has_file": false,
      "file_type": null,
      "file_url": null,
      "file_name": null,
      "created_at": "2025-11-09T08:58:32.657584",
      "is_pinned": false
    },
    {
      "id": 243,
      "title": "Yet beautiful go those.",
      "content": "Owner entire able style form end. Something energy wrong individual color produce. Law produce court improve sound tough treat dream. Body should interview wonder deal music dog.\n\nCheck this link: http://www.love-king.org/",
      "author": {
        "id": 744,
        "username": "nicholselizabeth",
        "mobile": "+1-506-921-1997x6803",
        "is_admin": false,
        "status": true,
        "created_at": "2025-04-06T21:29:58.820408",
        "email": "hrodriguez@example.net"
      },
      "has_file": false,
      "file_type": null,
      "file_url": null,
      "file_name": null,
      "created_at": "2025-11-10T12:23:12.260699",
      "is_pinned": false
    },
    {
      "id": 312,
      "title": "Without blue.",
      "content": "Simple water authority. Red seat couple fund door others however. Spring film amount beyond discuss read. Lose close relate nor. Suggest yeah improve occur. Mouth almost together their.",
      "author": {
        "id": 74,
        "username": "fmcguire",
        "mobile": "+1-355-594-8086",
        "is_admin": false,
        "status": false,
        "created_at": "2025-03-11T19:51:03.025443",
        "email": "russobrandon@example.net"
      },
      "has_file": false,
      "file_type": null,
      "file_url": null,
      "file_name": null,
      "created_at": "2025-11-16T01:49:33.399217",
      "is_pinned": true
    }
  ],
  "/api/assignments": [
    {
      "id": 26,
      "title": "Assignment 5: Optional didactic paradigm",
      "description": "Read chapter 9 and solve the problems.",
      "due_date": "2025-11-30T13:28:09.437757",
      "topic": {
        "id": 27,
        "name": "Algorithms",
        "description": "Fundamental concepts and practical applications. Week record left area.",
        "created_at": "2025-03-16T03:35:20.278527",
        "material_count": 6
      },
      "status": "pending",
      "points": 66,
      "created_at": "2025-11-06T17:26:55.772041"
    },
    {
      "id": 43,
      "title": "Assignment 3: Vision-oriented actuating artificial intelligence",
      "description": "Read chapter 8 and solve the problems.",
      "due_date": "2025-11-27T19:04:18.089322",
      "topic": {
        "id": 12,
        "name": "Natural Language Processing",
        "description": "Industry best practices and emerging trends. Without seem nor.",
        "created_at": "2025-10-06T13:30:29.885149",
        "material_count": 15
      },
      "status": "pending",
      "points": 79,
      "created_at": "2025-10-24T07:11:31.582799"
    },
    {
      "id": 150,
      "title": "Assignment 20: Switchable client-driven customer loyalty",
      "description": "Calculate the integral: $\\int_0^9 x^2 dx$",
      "due_date": "2025-12-18T04:13:28.697804",
      "topic": {
        "id": 12,
        "name": "Natural Language Processing",
        "description": "Industry best practices and emerging trends. Without seem nor.",
        "created_at": "2025-10-06T13:30:29.885149",
        "material_count": 15
      },
      "status": "pending",
      "points": 10,
      "created_at": "2025-10-28T22:13:03.109459"
    },
    {
      "id": 98,
      "title": "Assignment 5: Synchronized web-enabled standardization",
      "description": "Solve the following equation: $x^3 + 2x + 7 = 0$",
      "due_date": "2025-11-25T00:18:46.932866",
      "topic": {
        "id": 23,
        "name": "Network Security",
        "description": "Comprehensive coverage of principles and implementations. Or democratic policy teach relate writer despite.",
        "created_at": "2025-08-04T22:15:49.974803",
        "material_count": 10
      },
      "status": "due_soon",
      "points": 48,
      "created_at": "2025-11-13T13:29:39.683784"
    },
    {
      "id": 120,
      "title": "Assignment 19: Multi-channeled solution-oriented pricing structure",
      "description": "Prove that $\\sqrt[4]{16} = 2$",
      "due_date": "2025-12-03T16:30:38.717520",
      "topic": {
        "id": 38,
        "name": "Algorithms",
        "description": "Advanced techniques and real-world case studies. Power staff perhaps medical.",
        "created_at": "2025-07-08T17:53:23.095681",
        "material_count": 7
      },
      "status": "pending",
      "points": 11,
      "created_at": "2025-11-02T14:58:29.214557"
    },
    {
      "id": 128,
      "title": "Assignment 9: Polarized real-time ability",
      "description": "Prove that $\\sqrt[4]{13} = 3$",
      "due_date": "2025-11-22T01:49:17.560900",
      "topic": {
        "id": 9,
        "name": "Computer Vision",
        "description": "Hands-on projects and theoretical foundations. Figure wish rich trouble office game.",
        "created_at": "2025-11-02T20:45:10.991987",
        "material_count": 15
      },
      "status": "due_today",
      "points": 44,
      "created_at": "2025-11-06T21:02:43.491234"
    },
    {
      "id": 58,
      "title": "Assignment 16: Distributed client-server infrastructure",
      "description": "Read chapter 3 and solve the problems.",
      "due_date": "2025-11-24T10:13:59.953010",
      "topic": {
        "id": 27,
        "name": "Algorithms",
        "description": "Fundamental concepts and practical applications. Week record left area.",
        "created_at": "2025-03-16T03:35:20.278527",
        "material_count": 6
      },
      "status": "due_soon",
      "points": 73,
      "created_at": "2025-11-01T06:00:15.470088"
    },
    {
      "id": 165,
      "title": "Assignment 13: Devolved static access",
      "description": "Prove that $\\sqrt[3]{30} = 3$",
      "due_date": "2025-12-05T09:57:26.423295",
      "topic": {
        "id": 38,
        "name": "Algorithms",
        "description": "Advanced techniques and real-world case studies. Power staff perhaps medical.",
        "created_at": "2025-07-08T17:53:23.095681",
        "material_count": 7
      },
      "status": "pending",
      "points": 65,
      "created_at": "2025-11-13T10:47:06.690051"
    },
    {
      "id": 87,
      "title": "Assignment 3: Upgradable reciprocal matrix",
      "description": "Calculate the integral: $\\int_0^8 x^1 dx$",
      "due_date": "2025-12-04T16:34:26.019654",
      "topic": {
        "id": 23,
        "name": "Network Security",
        "description": "Comprehensive coverage of principles and implementations. Or democratic policy teach relate writer despite.",
        "created_at": "2025-08-04T22:15:49.974803",
        "material_count": 10
      },
      "status": "pending",
      "points": 98,
      "created_at": "2025-10-25T09:04:55.253533"
    },
    {
      "id": 102,
      "title": "Assignment 19: Face-to-face maximized throughput",
      "description": "Complete the exercises on Draw.",
      "due_date": "2025-12-15T04:48:43.381382",
      "topic": {
        "id": 36,
        "name": "Network Security",
        "description": "Advanced techniques and real-world case studies. Place language tell during require PM direction.",
        "created_at": "2025-02-08T19:18:43.897250",
        "material_count": 11
      },
      "status": "pending",
      "points": 56,
      "created_at": "2025-11-19T17:34:35.744420"
    },
    {
      "id": 21,
      "title": "Assignment 4: User-centric bi-directional middleware",
      "description": "Research and write a report about Multi-channeled coherent definition.",
      "due_date": "2025-12-05T20:15:45.377132",
      "topic": {
        "id": 12,
        "name": "Natural Language Processing",
        "description": "Industry best practices and emerging trends. Without seem nor.",
        "created_at": "2025-10-06T13:30:29.885149",
        "material_count": 15
      },
      "status": "pending",
      "points": 56,
      "created_at": "2025-10-25T21:20:24.640391"
    },
    {
      "id": 105,
      "title": "Assignment 9: Quality-focused stable core",
      "description": "Research and write a report about Focused user-facing toolset.",
      "due_date": "2025-12-19T00:10:03.894305",
      "topic": {
        "id": 36,
        "name": "Network Security",
        "description": "Advanced techniques and real-world case studies. Place language tell during require PM direction.",
        "created_at": "2025-02-08T19:18:43.897250",
        "material_count": 11
      },
      "status": "pending",
      "points": 65,
      "created_at": "2025-10-23T06:58:17.175846"
    }
  ],
  "/api/topics": [
    {
      "id": 38,
      "name": "Algorithms",
      "description": "Advanced techniques and real-world case studies. Power staff perhaps medical.",
      "created_at": "2025-07-08T17:53:23.095681",
      "material_count": 7
    },
    {
      "id": 12,
      "name": "Natural Language Processing",
      "description": "Industry best practices and emerging trends. Without seem nor.",
      "created_at": "2025-10-06T13:30:29.885149",
      "material_count": 15
    },
    {
      "id": 36,
      "name": "Network Security",
      "description": "Advanced techniques and real-world case studies. Place language tell during require PM direction.",
      "created_at": "2025-02-08T19:18:43.897250",
      "material_count": 11
    },
    {
      "id": 27,
      "name": "Algorithms",
      "description": "Fundamental concepts and practical applications. Week record left area.",
      "created_at": "2025-03-16T03:35:20.278527",
      "material_count": 6
    },
    {
      "id": 6,
      "name": "Operating Systems",
      "description": "Industry best practices and emerging trends. Out artist rather past.",
      "created_at": "2025-09-27T04:20:06.527044",
      "material_count": 11
    },
    {
      "id": 9,
      "name": "Computer Vision",
      "description": "Hands-on projects and theoretical foundations. Figure wish rich trouble office game.",
      "created_at": "2025-11-02T20:45:10.991987",
      "material_count": 15
    },
    {
      "id": 23,
      "name": "Network Security",
      "description": "Comprehensive coverage of principles and implementations. Or democratic policy teach relate writer despite.",
      "created_at": "2025-08-04T22:15:49.974803",
      "material_count": 10
    },
    {
      "id": 47,
      "name": "Algorithms",
      "description": "Industry best practices and emerging trends. Behavior all until recent economy already various.",
      "created_at": "2025-07-11T21:28:26.442814",
      "material_count": 6
    }
  ],
  "/api/timetable": [
    {
      "day": "Monday",
      "slots": [
        {
          "subject": "Algorithms",
          "teacher": "Michael Abbott",
          "time": "11:30-13:00",
          "room": "Virtual",
          "type": "Tutorial"
        },
        {
          "subject": "Network Security",
          "teacher": "Melanie Lopez",
          "time": "17:30-19:00",
          "room": "Room 105",
          "type": "Tutorial"
        },
        {
          "subject": "Algorithms",
          "teacher": "John Barr",
          "time": "17:30-19:00",
          "room": "Room 201",
          "type": "Lab"
        }
      ]
    },
    {
      "day": "Tuesday",
      "slots": [
        {
          "subject": "Physics",
          "teacher": "Ryan White",
          "time": "08:00-09:30",
          "room": "Virtual",
          "type": "Lecture"
        },
        {
          "subject": "Mathematics",
          "teacher": "Stacie Elliott",
          "time": "15:45-17:15",
          "room": "Lab 402",
          "type": "Lecture"
        },
        {
          "subject": "Physics",
          "teacher": "Mr. Michael Ellis MD",
          "time": "15:45-17:15",
          "room": "Virtual",
          "type": "Lab"
        }
      ]
    },
    {
      "day": "Wednesday",
      "slots": [
        {
          "subject": "Database Systems",
          "teacher": "Brandon Hernandez",
          "time": "08:00-09:30",
          "room": "Virtual",
          "type": "Lab"
        },
        {
          "subject": "Network Security",
          "teacher": "Michael Wallace",
          "time": "11:30-13:00",
          "room": "Room 105",
          "type": "Lab"
        },
        {
          "subject": "Algorithms",
          "teacher": "Melissa White",
          "time": "14:00-15:30",
          "room": "Room 105",
          "type": "Lab"
        },
        {
          "subject": "Mobile Development",
          "teacher": "John Combs",
          "time": "17:30-19:00",
          "room": "Virtual",
          "type": "Lecture"
        }
      ]
    },
    {
      "day": "Thursday",
      "slots": [
        {
          "subject": "Data Structures",
          "teacher": "Charles Fields",
          "time": "08:00-09:30",
          "room": "Lab 402",
          "type": "Lab"
        },
        {
          "subject": "Algorithms",
          "teacher": "Terrance Boyer",
          "time": "08:00-09:30",
          "room": "Virtual",
          "type": "Lab"
        },
        {
          "subject": "Mathematics",
          "teacher": "Shannon Wilson",
          "time": "15:45-17:15",
          "room": "Room 105",
          "type": "Lecture"
        },
        {
          "subject": "Data Structures",
          "teacher": "Katrina Williams",
          "time": "17:30-19:00",
          "room": "Room 305",
          "type": "Tutorial"
        },
        {
          "subject": "Physics",
          "teacher": "Edward Watkins",
          "time": "17:30-19:00",
          "room": "Lab 402",
          "type": "Tutorial"
        }
      ]
    },
    {
      "day": "Friday",
      "slots": [
        {
          "subject": "Algorithms",
          "teacher": "Patrick Reyes",
          "time": "08:00-09:30",
          "room": "Room 105",
          "type": "Lecture"
        },
        {
          "subject": "Data Structures",
          "teacher": "Kara Khan",
          "time": "15:45-17:15",
          "room": "Virtual",
          "type": "Tutorial"
        },
        {
          "subject": "Algorithms",
          "teacher": "Jeremiah Lloyd",
          "time": "17:30-19:00",
          "room": "Virtual",
          "type": "Lecture"
        }
      ]
    }
  ],
  "/api/timetable/grouped": [
    {
      "day": "Monday",
      "slots": [
        {
          "subject": "Algorithms",
          "teacher": "Michael Abbott",
          "time": "11:30-13:00",
          "room": "Virtual",
          "type": "Tutorial"
        },
        {
          "subject": "Network Security",
          "teacher": "Melanie Lopez",
          "time": "17:30-19:00",
          "room": "Room 105",
          "type": "Tutorial"
        },
        {
          "subject": "Algorithms",
          "teacher": "John Barr",
          "time": "17:30-19:00",
          "room": "Room 201",
          "type": "Lab"
        }
      ]
    },
    {
      "day": "Tuesday",
      "slots": [
        {
          "subject": "Physics",
          "teacher": "Ryan White",
          "time": "08:00-09:30",
          "room": "Virtual",
          "type": "Lecture"
        },
        {
          "subject": "Mathematics",
          "teacher": "Stacie Elliott",
          "time": "15:45-17:15",
          "room": "Lab 402",
          "type": "Lecture"
        },
        {
          "subject": "Physics",
          "teacher": "Mr. Michael Ellis MD",
          "time": "15:45-17:15",
          "room": "Virtual",
          "type": "Lab"
        }
      ]
    },
    {
      "day": "Wednesday",
      "slots": [
        {
          "subject": "Database Systems",
          "teacher": "Brandon Hernandez",
          "time": "08:00-09:30",
          "room": "Virtual",
          "type": "Lab"
        },
        {
          "subject": "Network Security",
          "teacher": "Michael Wallace",
          "time": "11:30-13:00",
          "room": "Room 105",
          "type": "Lab"
        },
        {
          "subject": "Algorithms",
          "teacher": "Melissa White",
          "time": "14:00-15:30",
          "room": "Room 105",
          "type": "Lab"
        },
        {
          "subject": "Mobile Development",
          "teacher": "John Combs",
          "time": "17:30-19:00",
          "room": "Virtual",
          "type": "Lecture"
        }
      ]
    },
    {
      "day": "Thursday",
      "slots": [
        {
          "subject": "Data Structures",
          "teacher": "Charles Fields",
          "time": "08:00-09:30",
          "room": "Lab 402",
          "type": "Lab"
        },
        {
          "subject": "Algorithms",
          "teacher": "Terrance Boyer",
          "time": "08:00-09:30",
          "room": "Virtual",
          "type": "Lab"
        },
        {
          "subject": "Mathematics",
          "teacher": "Shannon Wilson",
          "time": "15:45-17:15",
          "room": "Room 105",
          "type": "Lecture"
        },
        {
          "subject": "Data Structures",
          "teacher": "Katrina Williams",
          "time": "17:30-19:00",
          "room": "Room 305",
          "type": "Tutorial"
        },
        {
          "subject": "Physics",
          "teacher": "Edward Watkins",
          "time": "17:30-19:00",
          "room": "Lab 402",
          "type": "Tutorial"
        }
      ]
    },
    {
      "day": "Friday",
      "slots": [
        {
          "subject": "Algorithms",
          "teacher": "Patrick Reyes",
          "time": "08:00-09:30",
          "room": "Room 105",
          "type": "Lecture"
        },
        {
          "subject": "Data Structures",
          "teacher": "Kara Khan",
          "time": "15:45-17:15",
          "room": "Virtual",
          "type": "Tutorial"
        },
        {
          "subject": "Algorithms",
          "teacher": "Jeremiah Lloyd",
          "time": "17:30-19:00",
          "room": "Virtual",
          "type": "Lecture"
        }
      ]
    }
  ]
}

@app.route('/api/user')
def get_current_user():
    """Get current user data"""
    return jsonify(MOCK_DATA['/api/user'])

@app.route('/api/announcements')
def get_announcements():
    """Get all announcements"""
    return jsonify(MOCK_DATA['/api/announcements'])

@app.route('/api/assignments')
def get_assignments():
    """Get all assignments"""
    return jsonify(MOCK_DATA['/api/assignments'])

@app.route('/api/topics')
def get_topics():
    """Get all topics/units"""
    return jsonify(MOCK_DATA['/api/topics'])

@app.route('/api/timetable')
def get_timetable():
    """Get timetable (flat structure)"""
    flat_slots = []
    for day in MOCK_DATA['/api/timetable/grouped']:
        for slot in day['slots']:
            flat_slots.append({**slot, 'day': day['day']})
    return jsonify(flat_slots)

@app.route('/api/timetable/grouped')
def get_timetable_grouped():
    """Get timetable grouped by days"""
    return jsonify(MOCK_DATA['/api/timetable/grouped'])

@app.route('/api/track-visit', methods=['POST'])
def track_visit():
    """Track user visit (analytics)"""
    data = request.get_json()
    print(f"Visit tracked: {data}")
    return jsonify({'status': 'success'})

@app.route('/api/track-activity', methods=['POST'])
def track_activity():
    """Track user activity"""
    data = request.get_json()
    print(f"Activity tracked: {data}")
    return jsonify({'status': 'success'})

@app.route('/api/preview')
def get_link_preview():
    """Generate OG preview data"""
    url = request.args.get('url', '')
    return jsonify({
        'title': 'Sample Website - ' + random.choice(['Technology', 'Education', 'News', 'Blog']),
        'description': 'This is a sample description for the website preview.',
        'image': 'https://picsum.photos/200/100?random=' + str(random.randint(1, 100)),
        'url': url
    })
