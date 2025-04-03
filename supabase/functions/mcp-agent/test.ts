import { assertEquals } from 'https://deno.land/std@0.168.0/testing/asserts.ts'
import { handler } from './index.ts'

Deno.test('Edge Function - Portfolio Request', async () => {
  const request = new Request('http://localhost:8000', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ type: 'portfolio' }),
  })

  const response = await handler(request)
  const data = await response.json()

  assertEquals(response.status, 200)
  assertEquals(data.success, true)
  assertEquals(data.data.totalValue, 1000000)
  assertEquals(data.data.positions.length, 2)
})

Deno.test('Edge Function - Analysis Request', async () => {
  const request = new Request('http://localhost:8000', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ type: 'analysis' }),
  })

  const response = await handler(request)
  const data = await response.json()

  assertEquals(response.status, 200)
  assertEquals(data.success, true)
  assertEquals(data.data.riskLevel, 'medium')
  assertEquals(data.data.diversification, 'good')
  assertEquals(data.data.recommendations.length, 2)
})

Deno.test('Edge Function - Chat Request', async () => {
  const request = new Request('http://localhost:8000', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ type: 'chat' }),
  })

  const response = await handler(request)
  const data = await response.json()

  assertEquals(response.status, 200)
  assertEquals(data.success, true)
  assertEquals(typeof data.data.message, 'string')
})

Deno.test('Edge Function - Invalid Request Type', async () => {
  const request = new Request('http://localhost:8000', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ type: 'invalid' }),
  })

  const response = await handler(request)
  const data = await response.json()

  assertEquals(response.status, 400)
  assertEquals(data.success, false)
  assertEquals(data.error, 'Invalid request type')
}) 