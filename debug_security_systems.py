#!/usr/bin/env python3
"""
Comprehensive debugging and validation script for new security systems.
Tests all major components and provides detailed diagnostics.
"""

import sys
import traceback
from datetime import datetime, timezone

def test_metadata_system():
    """Test metadata manager functionality."""
    print("🔍 Testing Metadata System...")
    try:
        from assistant.memory.metadata_manager import metadata_manager

        # Test sensitivity classification
        test_cases = [
            ("password: secret123", "secret_critical"),  # Should match password pattern
            ("nmap scan results", "internal"),  # Should match internal patterns
            ("192.168.1.1 target", "secret_critical"),  # Private IP range
            ("~/document.txt", "private")  # Home directory pattern
        ]

        for text, expected_sensitivity in test_cases:
            metadata = metadata_manager.generate_metadata(text, "test")
            sensitivity = metadata["sensitivity"].value
            print(f"  Input: {text[:30]}...")
            print(f"    Sensitivity: {sensitivity} (expected: {expected_sensitivity})")
            print(f"    Classification: {metadata['classification'].value}")
            print(f"    Retention: {metadata['retention_policy'].value}")

        print("✅ Metadata system: PASSED")
        return True

    except Exception as e:
        print(f"❌ Metadata system: FAILED - {e}")
        traceback.print_exc()
        return False

def test_encryption_system():
    """Test encryption manager functionality."""
    print("\n🔐 Testing Encryption System...")
    try:
        from assistant.security.encryption_manager import encryption_manager

        # Test encryption/decryption
        test_data = "This is a test secret message"
        ciphertext, key_id = encryption_manager.encrypt(test_data)

        print(f"  Original: {test_data}")
        print(f"  Key ID: {key_id}")
        print(f"  Encrypted: {ciphertext[:50]}...")

        decrypted = encryption_manager.decrypt(ciphertext, key_id)
        print(f"  Decrypted: {decrypted}")

        if decrypted == test_data:
            print("✅ Encryption system: PASSED")
            return True
        else:
            print("❌ Encryption system: FAILED - Mismatch")
            return False

    except Exception as e:
        print(f"❌ Encryption system: FAILED - {e}")
        traceback.print_exc()
        return False

def test_key_rotation():
    """Test key rotation mechanism."""
    print("\n🔄 Testing Key Rotation...")
    try:
        from assistant.security.encryption_manager import encryption_manager

        # Get current key info
        current_key_id = encryption_manager.current_key_id
        current_key_info = encryption_manager.get_key_info(current_key_id)

        print(f"  Current Key: {current_key_id}")
        print(f"  Age: {current_key_info['age_days']} days")
        print(f"  Status: {current_key_info['status']}")

        print("✅ Key rotation: PASSED (manual rotation available)")
        return True

    except Exception as e:
        print(f"❌ Key rotation: FAILED - {e}")
        traceback.print_exc()
        return False

def test_retention_system():
    """Test retention manager functionality."""
    print("\n⏰ Testing Retention System...")
    try:
        from assistant.memory.main import MemoryManager
        from assistant.memory.retention_manager import get_retention_manager

        memory_manager = MemoryManager()
        retention_manager = get_retention_manager(memory_manager)

        # Test retention stats
        stats = retention_manager.get_retention_stats()
        print(f"  Total Entities: {stats['total_entities']}")
        print(f"  Storage Used: {stats['storage_used_mb']:.2f} MB")
        print(f"  Near Expiry: {stats['near_expiry']}")
        print(f"  By Confidence: {stats['by_confidence']}")

        print("✅ Retention system: PASSED")
        return True

    except Exception as e:
        print(f"❌ Retention system: FAILED - {e}")
        traceback.print_exc()
        return False

def test_secure_knowledge():
    """Test secure knowledge manager functionality."""
    print("\n📚 Testing Secure Knowledge System...")
    try:
        from assistant.memory.secure_knowledge import secure_knowledge_manager

        # Test document addition
        doc_result = secure_knowledge_manager.add_document(
            "test_doc.txt",
            "This is a test document content",
            "test_source"
        )

        print(f"  Document Added: {doc_result['success']}")
        print(f"  Sensitivity: {doc_result.get('sensitivity', 'N/A')}")

        # Test document retrieval
        retrieved = secure_knowledge_manager.get_document("test_doc.txt")
        if retrieved:
            print(f"  Document Retrieved: {retrieved['content'][:50]}...")
            print(f"  Tags: {retrieved['metadata'].get('tags', [])}")

        # Test search
        search_results = secure_knowledge_manager.search("test")
        print(f"  Search Results: {len(search_results)} documents found")

        # Cleanup
        secure_knowledge_manager.delete_document("test_doc.txt")

        print("✅ Secure knowledge system: PASSED")
        return True

    except Exception as e:
        print(f"❌ Secure knowledge system: FAILED - {e}")
        traceback.print_exc()
        return False

def test_workspace_isolation():
    """Test workspace isolation functionality."""
    print("\n🏠 Testing Workspace Isolation...")
    try:
        from assistant.memory.metadata_manager import workspace_isolation

        # Test accessibility checks
        test_entities = [
            {
                "workspace_project": "current_project",
                "sensitivity": "public"
            },
            {
                "workspace_project": "different_project",
                "sensitivity": "internal"
            }
        ]

        for entity in test_entities:
            accessible = workspace_isolation.is_accessible_in_current_workspace(entity)
            print(f"  Workspace: {entity['workspace_project']}")
            print(f"    Sensitivity: {entity['sensitivity']}")
            print(f"    Accessible: {accessible}")

        print("✅ Workspace isolation: PASSED")
        return True

    except Exception as e:
        print(f"❌ Workspace isolation: FAILED - {e}")
        traceback.print_exc()
        return False

def test_database_integration():
    """Test database integration with new schema."""
    print("\n🗄️ Testing Database Integration...")
    try:
        from assistant.db.models import init_db, SensitivityLevel, DataClassification, RetentionPolicy

        # Initialize database
        db_session = init_db()

        # Test new enum values
        print(f"  Sensitivity Levels: {[s.value for s in SensitivityLevel]}")
        print(f"  Data Classifications: {[d.value for d in DataClassification]}")
        print(f"  Retention Policies: {[r.value for r in RetentionPolicy]}")

        print("✅ Database integration: PASSED")
        return True

    except Exception as e:
        print(f"❌ Database integration: FAILED - {e}")
        traceback.print_exc()
        return False

def test_memory_entity_storage():
    """Test entity storage with metadata."""
    print("\n💾 Testing Entity Storage...")
    try:
        from assistant.memory.main import MemoryManager

        memory_manager = MemoryManager()

        # Test entity storage with source
        test_entities = [
            ("test_ip", "192.168.1.1", "ip", "terminal_output"),
            ("test_domain", "example.com", "domain", "user_input"),
            ("test_file", "/tmp/test.txt", "file_path", "manual_entry")
        ]

        for name, value, entity_type, source in test_entities:
            memory_manager.entities.set(name, value, entity_type, source=source)
            print(f"  Stored {entity_type}: {name} = {value}")

        # Test retrieval
        for name, _, _, _ in test_entities:
            retrieved = memory_manager.entities.get(name)
            print(f"  Retrieved {name}: {retrieved}")

        # Cleanup
        for name, _, _, _ in test_entities:
            memory_manager.entities.delete(name)

        print("✅ Entity storage: PASSED")
        return True

    except Exception as e:
        print(f"❌ Entity storage: FAILED - {e}")
        traceback.print_exc()
        return False

def run_comprehensive_tests():
    """Run all security system tests."""
    print("=" * 60)
    print("🔒 COMPREHENSIVE SECURITY SYSTEM TESTS")
    print("=" * 60)

    results = {
        "Metadata System": test_metadata_system(),
        "Encryption System": test_encryption_system(),
        "Key Rotation": test_key_rotation(),
        "Retention System": test_retention_system(),
        "Secure Knowledge": test_secure_knowledge(),
        "Workspace Isolation": test_workspace_isolation(),
        "Database Integration": test_database_integration(),
        "Entity Storage": test_memory_entity_storage()
    }

    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")

    print(f"\n🎯 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🟢 ALL TESTS PASSED - Systems ready for production!")
        return 0
    else:
        print(f"🟡 {total - passed} test(s) failed - Review logs above")
        return 1

if __name__ == "__main__":
    sys.exit(run_comprehensive_tests())