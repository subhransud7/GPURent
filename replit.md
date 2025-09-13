# Overview

This is a peer-to-peer GPU cloud platform that enables users to share and rent GPU computing resources. The platform consists of a React frontend with a FastAPI backend, supporting both GPU hosts (who provide computing power) and renters (who need GPU resources). The system uses Google OAuth for authentication and includes real-time communication via WebSockets for job management and host monitoring.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: React 19 with Vite as the build tool
- **Styling**: Tailwind CSS v4 for responsive design
- **UI Components**: Headless UI and Heroicons for accessible components
- **Routing**: React Router DOM for client-side navigation
- **HTTP Client**: Axios for API communication
- **Development Setup**: Configured for Replit hosting with proxy to backend

## Backend Architecture
- **Framework**: FastAPI with async/await support
- **Database**: SQLAlchemy ORM with PostgreSQL (configurable via DATABASE_URL)
- **Authentication**: JWT tokens with Google OAuth integration
- **Real-time Communication**: WebSocket connections for live updates
- **Job Queue**: Redis-based queue system for GPU job management
- **API Design**: RESTful endpoints with Pydantic schemas for validation

## Data Models
The system uses four core entities:
- **Users**: Support multiple roles (host, renter, admin) with Google OAuth profiles
- **Hosts**: GPU providers with hardware specifications and availability status
- **Jobs**: Computing tasks with status tracking and progress monitoring
- **Public Models**: Shared machine learning models available across the platform

## Authentication & Authorization
- **OAuth Provider**: Google OAuth 2.0 for user authentication
- **Token Management**: JWT tokens with configurable expiration
- **Role-based Access**: Different permissions for hosts, renters, and admins
- **WebSocket Auth**: Token-based authentication for real-time connections

## Job Management System
- **Queue Architecture**: Redis-based job queuing with status tracking
- **Real-time Updates**: WebSocket connections for live job progress
- **Host Communication**: Heartbeat system for monitoring GPU availability
- **Error Handling**: Comprehensive error tracking and recovery mechanisms

# External Dependencies

## Core Services
- **PostgreSQL**: Primary database for persistent data storage
- **Redis**: Job queue management and caching layer
- **Google OAuth**: Authentication service for user login

## Payment Integration
- **Stripe**: Payment processing for GPU rentals (customer and Connect accounts)

## Cloud Services
- **AWS S3**: File storage via boto3 (likely for model artifacts and job outputs)

## Development Tools
- **Docker**: Containerization support for GPU host environments
- **NVIDIA Management**: pynvml for GPU monitoring and management

## Frontend Libraries
- **Tailwind CSS**: Utility-first CSS framework
- **Headless UI**: Accessible React components
- **Heroicons**: SVG icon library
- **React Router**: Client-side routing

## Backend Libraries
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: Database ORM and migrations
- **Redis-py**: Redis client for Python
- **python-jose**: JWT token handling
- **Pydantic**: Data validation and serialization