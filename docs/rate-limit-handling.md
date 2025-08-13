# Rate Limit Handling

Cuti automatically handles Claude rate limits with intelligent retry logic.

## How it works

When Claude returns a rate limit message like:
```
Claude usage limit reached. Your limit will reset at 9pm (America/New_York).
```

Cuti will:
1. Parse the exact reset time with timezone
2. Pause the queue and wait for the reset
3. Display countdown to next retry
4. Automatically resume with "continue" after reset

## Supported formats

- `Your limit will reset at 9pm (America/New_York)`
- `Your limit will reset at 11:30pm (America/Los_Angeles)`
- Generic rate limit messages (5-minute cooldown)

## Queue behavior

Rate-limited prompts:
- Keep their position in the queue
- Show status as `RATE_LIMITED`
- Display reset time in logs
- Retry automatically when limit resets
- Use "continue" to resume conversation

## Monitoring

Check rate limit status:
```bash
cuti status
```

The web UI shows:
- Rate-limited prompts
- Reset times
- Automatic retry schedule

## Configuration

Default retry settings:
- Max retries: 3
- Check interval: 60 seconds (or less near reset)
- Automatic "continue" on retry

## Manual intervention

If needed, cancel a rate-limited prompt:
```bash
cuti queue remove <prompt-id>
```