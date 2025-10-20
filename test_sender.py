import asyncio
from datetime import timedelta
from slim_bindings.slim import Slim, PyName, PyIdentityProvider, PyIdentityVerifier
from slim_bindings.session import PySessionConfiguration

async def main():
    print("=== SENDER ===")
    name = PyName("agntcy", "nanda", "sender-agent")
    provider = PyIdentityProvider.SharedSecret(identity="sender", shared_secret="test-secret")
    verifier = PyIdentityVerifier.SharedSecret(identity="sender", shared_secret="test-secret")
    
    slim = await Slim.new(name, provider, verifier)
    conn_id = await slim.connect({"endpoint": "http://localhost:46357", "tls": {"insecure": True}})
    print(f"✅ Connected: {conn_id}, ID: {slim.id}")
    
    # CRITICAL: Set route before creating session
    peer_name = PyName("agntcy", "nanda", "receiver-agent")
    await slim.set_route(peer_name)
    print(f"✅ Route set to receiver-agent")
    
    # Create PointToPoint session
    config = PySessionConfiguration.PointToPoint(
        peer_name=peer_name,
        timeout=timedelta(seconds=5),
        max_retries=5,
        mls_enabled=False
    )
    
    session = await slim.create_session(config)
    print(f"✅ Session created: {session.id}")
    
    # Send message
    message = "Hello from sender!"
    await session.publish(message.encode('utf-8'))
    print(f"📤 Sent: {message}")
    
    # Wait for reply
    msg_ctx, reply = await session.get_message()
    print(f"📥 Received reply: {reply.decode('utf-8')}")
    
    await session.delete()
    await slim.disconnect("http://localhost:46357")

if __name__ == "__main__":
    asyncio.run(main())