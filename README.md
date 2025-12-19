# Exam Platform API

Kidemia is a modern api project built with FastAPI for speed, reliability, and scalability.
It features Domain-Driven Design (DDD) architecture and repository pattern. The API serves as the foundation for APIs powering Kidemia applications.


## 🎯 Features

### Core Features
- **User Management**: Students, Guardians, Institution Admins, Platform Admins
- **Content Management**: Subjects, Topics, Questions with various option types
- **Assessments**: Free tests and paid exams
- **Institution Management**: Onboarding and student enrollment
- **Gamification**: Points, badges, leaderboards, challenges
- **Proctoring**: Session monitoring, violation detection
- **AI Assistant**: Concept explanations during tests
- **Results & Analytics**: Auto-grading, performance tracking
- **Forum**: Discussion threads, Q&A
- **Payment Integration**: Stripe, Paystack support

### Technical Features
- Domain-Driven Design (DDD) architecture
- Repository pattern for database abstraction
- JWT-based authentication with refresh tokens
- Role-based access control (RBAC)
- Comprehensive exception handling
- API rate limiting
- Caching with Redis
- Background tasks with Celery
- File upload support (local & S3)
- Email notifications
- Comprehensive logging
- API documentation with Swagger

## 🏗️ Architecture

### Project Structure
```
exam_platform/
├── src/
│   ├── main.py                 # Application entry point
│   ├── config/                 # Configuration management
│   ├── core/                   # Core utilities (security, exceptions)
│   ├── shared/                 # Shared components (base classes)
│   ├── domains/                # Domain modules (DDD)
│   │   ├── auth/              # Authentication & authorization
│   │   ├── content/           # Academic content
│   │   ├── assessment/        # Tests and exams
│   │   ├── institution/       # Institution management
│   │   ├── gamification/      # Gamification features
│   │   ├── proctoring/        # Proctoring system
│   │   ├── ai_assistant/      # AI support
│   │   ├── results/           # Results & analytics
│   │   ├── forum/             # Discussion forum
│   │   ├── payment/           # Payment processing
│   │   └── guardian/          # Guardian management
│   └── api/                    # API routes
├── tests/                      # Test suite
├── alembic/                    # Database migrations
├── scripts/                    # Utility scripts
└── docs/                       # Documentation
```

### Domain Structure (Each Domain)
```
domain_name/
├── models/          # SQLAlchemy models
├── schemas/         # Pydantic schemas
├── repositories/    # Data access layer
├── services/        # Business logic layer
├── api/            # API endpoints
└── enums.py        # Domain enums
```

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- (Optional) Poetry for dependency management

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/ogbonnaohakwe/kidemia-backend
cd kidemia
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

Using uv:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

Using Poetry:
```bash
poetry install
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Set up database**
```bash
# Create database
createdb kidemia

# Run migrations
alembic upgrade head
```

6. **Seed initial data** (optional)
```bash
python scripts/seed_data.py
```

### Running the Application

**Development mode:**
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Production mode:**
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Using Python:**
```bash
python src/main.py
```

### Running with Docker

```bash
docker-compose up -d
```

## 📚 API Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

## 🧪 Testing

Run tests:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=src --cov-report=html
```

Run specific test file:
```bash
pytest tests/unit/test_auth.py
```

## 🗄️ Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback migration:
```bash
alembic downgrade -1
```

## 🔐 Authentication Flow

1. **Register**: `POST /api/v1/auth/register`
2. **Login**: `POST /api/v1/auth/login` → Returns access & refresh tokens
3. **Access Protected Routes**: Include `Authorization: Bearer <access_token>` header
4. **Refresh Token**: `POST /api/v1/auth/refresh` when access token expires
5. **Logout**: `POST /api/v1/auth/logout`

## 👥 User Types & Roles

### User Types
- **Student**: Takes tests and exams
- **Guardian**: Manages wards (students)
- **Institution Admin**: Manages institution and enrolls students
- **Platform Admin**: System administration

### Admin Types
- **Super Admin**: Full system access
- **Content Admin**: Manages questions and content
- **Support Admin**: Handles support tickets
- **Finance Admin**: Manages payments
- **Analytics Admin**: Views reports and analytics

## 🎮 Gamification System

### Points
- Correct answer: 10 points
- Test completion: 50 points
- Exam completion: 100 points
- Streak bonus: 1.5x multiplier

### Badges
- Achievement-based badges
- Milestone badges
- Special event badges

### Leaderboards
- Global leaderboard
- Subject-specific leaderboards
- Institution leaderboards
- Time-based leaderboards (daily, weekly, monthly)

## 🔍 Proctoring Features

- Screenshot capture at intervals
- Face detection monitoring
- Tab switching detection
- Copy-paste prevention
- Full-screen enforcement
- Browser extension detection
- Violation reporting

## 💳 Payment Integration

### Supported Gateways
- flutterwave
- Paystack

### Payment Features
- One-time payments for exams
- Subscription management
- Webhook handling
- Transaction history
- Refund processing

## 📧 Email Notifications

- Welcome email
- Email verification
- Password reset
- Exam reminders
- Result notifications
- Payment confirmations

## 🤖 AI Assistant

- Powered by OpenAI GPT-4 or Anthropic Claude
- Context-aware explanations
- Subject-specific guidance
- Learning path recommendations

## 📊 Analytics & Reporting

- Student performance tracking
- Institution analytics
- Question difficulty analysis
- Topic mastery tracking
- Engagement metrics
- Revenue reports

## 🔒 Security Features

- Password hashing with bcrypt
- JWT token authentication
- Refresh token rotation
- Account lockout after failed attempts
- CORS protection
- SQL injection prevention
- XSS protection
- Rate limiting
- Input validation
- Audit logging

## 🛠️ Development Guidelines

### Code Style
- Follow PEP 8
- Use Black for formatting
- Use isort for import sorting
- Type hints for all functions
- Docstrings for all modules, classes, and functions

### Commit Messages
```
feat: Add new feature
fix: Bug fix
docs: Documentation changes
style: Code style changes
refactor: Code refactoring
test: Test additions/changes
chore: Maintenance tasks
```

### Branch Strategy
- `main`: Production-ready code
- `develop`: Development branch
- `feature/*`: New features
- `bugfix/*`: Bug fixes
- `hotfix/*`: Urgent fixes

## 📝 Environment Variables

See `.env.example` for all available configuration options.

## curl http://localhost:8080/api/openapi.json -o ./src/sdk/openapi.json

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'feat: Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 👨‍💻 Support

For support, email support@kidemia.net or open an issue in the repository.

## 🗺️ Roadmap

### Phase 1 (Current)
- [x] Authentication system
- [ ] Content management
- [ ] Assessment system
- [ ] Basic gamification

### Phase 2
- [ ] Proctoring system
- [ ] AI assistant integration
- [ ] Advanced analytics
- [ ] Mobile app API

### Phase 3
- [ ] Live classes integration
- [ ] Video content support
- [ ] Advanced AI features
- [ ] Multi-language support

## 🙏 Acknowledgments

- FastAPI framework
- SQLAlchemy ORM
- Pydantic validation
- All contributors

---

**Built with ❤️ for Kidemia**