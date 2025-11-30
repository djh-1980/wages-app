"""
Customer Mapping API Routes
Handles customer mapping management endpoints
"""

from flask import Blueprint, request, jsonify
from app.models.customer_mapping import CustomerMappingModel

# Create blueprint
customer_mapping_bp = Blueprint('api_customer_mapping', __name__)

@customer_mapping_bp.route('/mappings', methods=['GET'])
def api_get_mappings():
    """Get all customer mappings."""
    try:
        model = CustomerMappingModel()
        mappings = model.get_all_mappings()
        
        return jsonify({
            'success': True,
            'mappings': mappings
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_mapping_bp.route('/mappings', methods=['POST'])
def api_add_mapping():
    """Add a new customer mapping."""
    try:
        data = request.json
        original_customer = data.get('original_customer', '').strip()
        mapped_customer = data.get('mapped_customer', '').strip()
        notes = data.get('notes', '').strip() or None
        
        if not original_customer or not mapped_customer:
            return jsonify({
                'success': False,
                'error': 'Both original and mapped customer names are required'
            }), 400
        
        model = CustomerMappingModel()
        result = model.add_mapping(original_customer, mapped_customer, notes)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_mapping_bp.route('/mappings/<int:mapping_id>', methods=['PUT'])
def api_update_mapping(mapping_id):
    """Update an existing customer mapping."""
    try:
        data = request.json
        original_customer = data.get('original_customer', '').strip()
        mapped_customer = data.get('mapped_customer', '').strip()
        notes = data.get('notes', '').strip() or None
        
        if not original_customer or not mapped_customer:
            return jsonify({
                'success': False,
                'error': 'Both original and mapped customer names are required'
            }), 400
        
        model = CustomerMappingModel()
        result = model.update_mapping(mapping_id, original_customer, mapped_customer, notes)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_mapping_bp.route('/mappings/<int:mapping_id>', methods=['DELETE'])
def api_delete_mapping(mapping_id):
    """Delete a customer mapping."""
    try:
        model = CustomerMappingModel()
        result = model.delete_mapping(mapping_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_mapping_bp.route('/customers', methods=['GET'])
def api_get_customers():
    """Get all unique customer names for dropdown/autocomplete."""
    try:
        model = CustomerMappingModel()
        customers = model.get_unique_customers()
        
        return jsonify({
            'success': True,
            'customers': customers
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_mapping_bp.route('/suggestions', methods=['GET'])
def api_get_suggestions():
    """Get suggested customer mappings based on similar names."""
    try:
        model = CustomerMappingModel()
        suggestions = model.get_mapping_suggestions()
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_mapping_bp.route('/stats', methods=['GET'])
def api_get_mapping_stats():
    """Get customer mapping statistics."""
    try:
        model = CustomerMappingModel()
        stats = model.get_mapping_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_mapping_bp.route('/resolve/<customer_name>', methods=['GET'])
def api_resolve_customer(customer_name):
    """Resolve a customer name to its mapped equivalent."""
    try:
        model = CustomerMappingModel()
        mapped_customer = model.get_mapped_customer(customer_name)
        
        return jsonify({
            'success': True,
            'original_customer': customer_name,
            'mapped_customer': mapped_customer,
            'is_mapped': mapped_customer != customer_name
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@customer_mapping_bp.route('/bulk-add', methods=['POST'])
def api_bulk_add_mappings():
    """Add multiple customer mappings at once."""
    try:
        data = request.json
        mappings = data.get('mappings', [])
        
        if not mappings:
            return jsonify({
                'success': False,
                'error': 'No mappings provided'
            }), 400
        
        model = CustomerMappingModel()
        results = []
        success_count = 0
        
        for mapping in mappings:
            original = mapping.get('original_customer', '').strip()
            mapped = mapping.get('mapped_customer', '').strip()
            notes = mapping.get('notes', '').strip() or None
            
            if original and mapped:
                result = model.add_mapping(original, mapped, notes)
                results.append({
                    'original_customer': original,
                    'mapped_customer': mapped,
                    'success': result['success'],
                    'error': result.get('error')
                })
                
                if result['success']:
                    success_count += 1
            else:
                results.append({
                    'original_customer': original,
                    'mapped_customer': mapped,
                    'success': False,
                    'error': 'Missing customer names'
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'success_count': success_count,
            'total_count': len(mappings)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
