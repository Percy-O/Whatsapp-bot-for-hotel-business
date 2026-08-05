# Hotel WhatsApp Bot

An AI-powered WhatsApp chatbot built with **FastAPI** that automates hotel guest communication. The bot integrates with the **WhatsApp Cloud API**, **Google Gemini AI**, and the **Spaxce Hotel Management API** to provide 24/7 customer support, room booking, pricing, availability checks, booking management, and guest assistance.

## Features

- 📱 WhatsApp Cloud API integration
- 🤖 AI-powered conversations using Google Gemini
- 🏨 Room availability lookup
- 🛏️ Room booking and reservation management
- 💰 Room pricing inquiries
- 🔍 Search existing bookings
- ❓ Frequently Asked Questions (FAQ)
- 👨‍💼 Escalate conversations to hotel staff
- 🔗 Spaxce Hotel Management API integration
- 🚀 FastAPI REST backend
- ❤️ Health check endpoint
- 🌐 Webhook verification for Meta WhatsApp

---

## Tech Stack

- Python 3.12+
- FastAPI
- Uvicorn
- Google Gemini API
- WhatsApp Cloud API
- HTTPX
- Jinja2
- Dateparser
- MySQL / PostgreSQL Support
- Python Dotenv

---

## Project Structure

```
hotel-bot/
│
├── main.py                 # FastAPI entry point
├── requirements.txt
├── render.yaml             # Render deployment
├── .env.example
│
├── src/
│   ├── agent.py
│   ├── webhook.py
│   ├── messenger.py
│   ├── router.py
│   ├── booking_handler.py
│   ├── payment.py
│   ├── session.py
│   ├── spaxce_api_client.py
│   │
│   └── handlers/
│       ├── availability.py
│       ├── booking.py
│       ├── pricing.py
│       ├── faq.py
│       ├── search_booking.py
│       └── escalate.py
│
└── tests/
```

---

## Installation

Clone the repository

```bash
git clone https://github.com/yourusername/hotel-bot.git

cd hotel-bot
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file using `.env.example`.

```env
# WhatsApp
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
VERIFY_TOKEN=

# Google Gemini
GEMINI_API_KEY=

# Spaxce API
SPAXCE_API_URL=
SPAXCE_API_TOKEN=

# Hotel
HOTEL_NAME=
STAFF_WHATSAPP=

# Server
PORT=8000
ENV=development
```

---

## Running the Application

Start the development server

```bash
uvicorn main:app --reload
```

The API will be available at

```
http://localhost:8000
```

Swagger Documentation

```
http://localhost:8000/api/docs
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Service health check |
| `GET /webhook` | Verify WhatsApp webhook |
| `POST /webhook` | Receive WhatsApp messages |

---

## Supported Guest Requests

The bot can assist guests with:

- Room availability
- Room pricing
- Booking reservations
- Booking lookup
- Reservation updates
- Hotel FAQs
- Human support escalation
- AI-powered conversations

---

## Deployment

The project includes a `render.yaml` configuration for deployment on **Render**.

To deploy:

1. Push the repository to GitHub.
2. Create a new Render Web Service.
3. Connect the repository.
4. Configure the required environment variables.
5. Deploy.

---

## Future Improvements

- Payment gateway integration
- Multi-language support
- Voice message support
- Image recognition
- Booking cancellation
- Guest feedback collection
- Analytics dashboard
- Multi-property support

---

## Contributing

Contributions are welcome. Feel free to fork the project, create a feature branch, and submit a pull request.

---

## License

This project is licensed under the MIT License.

---

## Author

**Percy Owoeye**

Software Engineer • AI Developer • Founder of TechOhr

Building AI-powered solutions that automate business operations and improve customer experiences.
