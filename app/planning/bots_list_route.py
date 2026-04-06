# Add this route to app/routes/bots_routes.py

@bots_bp.route('/bots/list', methods=['GET'])
def list_bots():
    """List all registered bots from Neo4j registry."""
    from app.services.neo4j_service import get_session
    
    session = get_session().__enter__()
    try:
        result = session.run("""
            MATCH (bf:BotFunction)
            RETURN bf.`bot-id` AS `bot-id`,
                   bf.use_case AS use_case,
                   bf.params AS params,
                   bf.module AS module,
                   bf.function AS function
            ORDER BY bf.`bot-id`
        """)
        
        bots = []
        for record in result:
            bots.append({
                "bot-id": record["bot-id"],
                "use_case": record["use_case"],
                "params": record["params"],
                "module": record["module"],
                "function": record["function"]
            })
        
        return jsonify({"bots": bots, "count": len(bots)})
        
    except Exception as e:
        return jsonify({"error": f"Failed to list bots: {str(e)}"}), 500
    finally:
        session.__exit__(None, None, None)
