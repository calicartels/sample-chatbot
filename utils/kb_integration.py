"""
Knowledge Base Integration Module

This module integrates the knowledge base builder with the document processing pipeline.
"""
import os
import json
import glob
from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import STRUCTURED_DIR
from utils.kb_builder import KnowledgeBaseBuilder

class KnowledgeBaseManager:
    """Manages knowledge base integration with the document processing pipeline."""
    
    def __init__(self):
        """Initialize the knowledge base manager."""
        self.kb_builder = KnowledgeBaseBuilder()
    
    def process_document_completion(self, doc_id):
        """
        Process document completion by building a comprehensive knowledge base.
        
        Args:
            doc_id (str): ID of the processed document
            
        Returns:
            str: ID of the created comprehensive knowledge base
        """
        print("\n🧩 Building comprehensive knowledge base...")
        kb_id = self.kb_builder.build_comprehensive_kb(doc_id)
        
        if kb_id:
            print(f"✅ Knowledge base {kb_id} created successfully")
            return kb_id
        else:
            print("❌ Failed to create knowledge base")
            return None
    
    def get_kb_by_doc_id(self, doc_id):
        """
        Find knowledge bases associated with a document ID.
        
        Args:
            doc_id (str): Document ID to search for
            
        Returns:
            list: List of knowledge base IDs
        """
        # Find all knowledge base files
        pattern = os.path.join(STRUCTURED_DIR, "kb_*.json")
        kb_files = glob.glob(pattern)
        
        # Check each file for the document ID in source_extractions
        related_kbs = []
        for kb_file in kb_files:
            try:
                with open(kb_file, 'r') as f:
                    kb_data = json.load(f)
                    
                    if '_metadata' in kb_data and 'source_extractions' in kb_data['_metadata']:
                        # Check if document ID is in source extractions
                        if any(doc_id in extraction for extraction in kb_data['_metadata']['source_extractions']):
                            kb_id = os.path.basename(kb_file).replace('.json', '')
                            related_kbs.append({
                                'id': kb_id,
                                'title': kb_data.get('title', 'Untitled'),
                                'created_at': kb_data['_metadata'].get('created_at', 'Unknown')
                            })
            except Exception as e:
                print(f"Error checking knowledge base {kb_file}: {e}")
        
        return related_kbs
    
    def get_latest_kb(self):
        """
        Get the latest comprehensive knowledge base.
        
        Returns:
            dict: Knowledge base data or None if not found
        """
        # Find all knowledge base files
        pattern = os.path.join(STRUCTURED_DIR, "kb_*.json")
        kb_files = glob.glob(pattern)
        
        if not kb_files:
            return None
        
        # Sort by modification time (newest first)
        kb_files.sort(key=os.path.getmtime, reverse=True)
        
        # Load the latest knowledge base
        try:
            with open(kb_files[0], 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading latest knowledge base: {e}")
            return None