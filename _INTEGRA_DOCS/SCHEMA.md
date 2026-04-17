# Integra Neural Engine — Database Schema
This document outlines the Supabase table structure required for the SaaS platform.

## 1. `agent_memories`
Stores the persistent conversational memory for each user.
- `id`: uuid, primary key
- `created_at`: timestamp with time zone
- `user_id`: uuid, foreign key (auth.users.id)
- `role`: text (e.g., 'human', 'ai')
- `content`: text

## 2. `external_mcps` (Matrix Nodes)
Stores linked third-party services (Stripe, Slack, etc.).
- `id`: uuid, primary key
- `user_id`: uuid, foreign key (auth.users.id)
- `mcp_name`: text
- `mcp_type`: text (e.g., 'stripe', 'rest_api')
- `mcp_config`: jsonb (credentials, base_url, etc.)
- `is_active`: boolean
- `created_at`: timestamp

## 3. `nodes` (Interview Sessions)
Stores active and historic interview node data.
- `id`: uuid, primary key
- `room_id`: text, unique
- `user_id`: uuid, foreign key (auth.users.id)
- `candidate_name`: text
- `candidate_email`: text
- `position`: text
- `scheduled_at`: timestamp
- `status`: text (e.g., 'active', 'completed')
- `metadata`: jsonb

## 4. `user_settings`
Global LLM and system settings per user.
- `user_id`: uuid, primary key
- `llm_provider`: text
- `llm_model`: text
- `llm_api_key`: text (Encrypted or server-side only)
- `system_prompt`: text

## 5. `profiles`
Extended user data and subscription status.
- `id`: uuid, primary key
- `email`: text
- `subscription_status`: text (e.g., 'free', 'pro', 'enterprise')
- `stripe_customer_id`: text
- `interviews_limit`: integer
- `usage_count`: integer
