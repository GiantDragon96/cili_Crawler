from flask import Flask, request, jsonify
import pymysql

app = Flask(__name__)

def get_db():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="12345",
        database="cili",
        cursorclass=pymysql.cursors.DictCursor
    )

@app.post("/api/sync/insertCili")
def insert_cili():
    data = request.get_json()

    conn = get_db()

    try:
        with conn.cursor() as cursor:
            # 1. check duplicate title
            cursor.execute(
                "SELECT id FROM cili_resources WHERE title = %s LIMIT 1",
                (data["title"],)
            )

            if cursor.fetchone():
                return jsonify({
                    "code": 1,
                    "msg": "Data already exists"
                })

            # 2. find category_id by tag
            cursor.execute(
                "SELECT id FROM category WHERE name = %s LIMIT 1",
                (data["tag"],)
            )

            category = cursor.fetchone()

            if not category:
                return jsonify({
                    "code": 1,
                    "msg": "Category not found"
                })

            # 3. insert resource
            sql = """
            INSERT INTO cili_resources (
                title,
                category_id,
                magnet_url,
                filename,
                actors,
                content,
                thumb,
                cover,
                series,
                publish_time,
                sub_tag,
                duration,
                maker,
                collect_page,
                size,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
            """

            cursor.execute(sql, (
                data["title"],
                category["id"],
                data["magnet_url"],
                data.get("filename"),
                data["actors"],
                data["content"],
                data["thumb"],
                data["cover"],
                data["series"],
                data["publish_time"],
                data["sub_tag"],
                data["duration"],
                data["maker"],
                data["collect_page"],
                data["size"],
            ))

            conn.commit()

            return jsonify({
                "code": 0,
                "id": cursor.lastrowid,
                "filename": data.get("filename")
            })

    except Exception as e:
        conn.rollback()
        return jsonify({
            "code": 1,
            "msg": str(e)
        })

    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True, port=5050)