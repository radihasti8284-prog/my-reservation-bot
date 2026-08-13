# ====== اضافه کردن مدیریت خطا در API نوبت‌ها ======
@app.route('/api/admin/appointments', methods=['GET'])
def admin_get_appointments():
    try:
        status = request.args.get('status')
        date = request.args.get('date')
        user = request.args.get('user')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        offset = (page - 1) * limit

        conn = get_db()
        cursor = conn.cursor()
        query = '''SELECT a.*, u.name as user_name, u.phone, u.telegram_id, s.name as service_name 
                   FROM appointments a 
                   JOIN users u ON a.user_id = u.id 
                   JOIN services s ON a.service_id = s.id 
                   WHERE 1=1'''
        params = []
        if status:
            query += " AND a.status = ?"
            params.append(status)
        if date:
            query += " AND a.appointment_date = ?"
            params.append(date)
        if user:
            query += " AND u.telegram_id = ?"
            params.append(user)

        # شمارش کل برای Pagination
        count_query = query.replace('SELECT a.*, u.name as user_name, u.phone, u.telegram_id, s.name as service_name', 'SELECT COUNT(*) as total')
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']

        query += " ORDER BY a.appointment_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        apps = cursor.fetchall()
        conn.close()

        return jsonify({
            "status": "ok",
            "appointments": [dict(a) for a in apps],
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit
            }
        })
    except Exception as e:
        print(f"❌ Error in admin_get_appointments: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500