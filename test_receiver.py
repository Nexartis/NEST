import asyncio
from slim_bindings.slim import Slim, PyName, PyIdentityProvider, PyIdentityVerifier

async def main():
    print("=== RECEIVER ===")
    name = PyName("agntcy", "nanda", "receiver-agent")
    provider = PyIdentityProvider.SharedSecret(identity="receiver", shared_secret="test-secret")
    verifier = PyIdentityVerifier.SharedSecret(identity="receiver", shared_secret="test-secret")
    
    slim = await Slim.new(name, provider, verifier)
    conn_id = await slim.connect({"endpoint": "http://localhost:46357", "tls": {"insecure": True}})
    print(f"✅ Connected: {conn_id}, ID: {slim.id}")
    
    print("⏳ Waiting for incoming session...")
    session = await slim.listen_for_session()
    print(f"✅ Got session: {session.id}")
    
    # Use get_message() instead of recv()
    msg_ctx, payload = await session.get_message()
    print(f"📥 Received: {payload.decode('utf-8')}")
    
    # Reply back
    reply = f"Echo: {payload.decode()} from receiver"
    await session.publish_to(msg_ctx, reply.encode('utf-8'))
    print(f"📤 Sent reply: {reply}")
    
    await slim.disconnect("http://localhost:46357")

if __name__ == "__main__":
    asyncio.run(main())