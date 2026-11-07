import os
from datetime import date
from flask import Flask, current_app, jsonify, render_template, session
from config import Config
from database.db import init_db, query_db
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.clientes import clientes_bp
from routes.creditos import creditos_bp
from routes.riesgos import riesgos_bp
from routes.morosidad import morosidad_bp
from routes.reportes import reportes_bp
from routes.geografia import geografia_bp
from routes.decisiones import decisiones_bp
from routes.salud import salud_bp
from routes.promesas import promesas_bp
from routes.telegram_webhook import telegram_bp
from services.telegram_service import iniciar_demonio_telegram

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    Config.validate()

    # La base local se prepara automáticamente; Supabase debe tener aplicado schema.sql.
    with app.app_context():
        try:
            init_db()
        except Exception as e:
            app.logger.exception("No se pudo inicializar o validar la base de datos")
            raise RuntimeError("No se pudo inicializar o validar la base de datos.") from e

    # Registro de Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(creditos_bp)
    app.register_blueprint(riesgos_bp)
    app.register_blueprint(morosidad_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(geografia_bp)
    app.register_blueprint(decisiones_bp)
    app.register_blueprint(salud_bp)
    app.register_blueprint(promesas_bp)
    app.register_blueprint(telegram_bp)

    @app.get('/health')
    def health():
        query_db("SELECT 1", one=True)
        return jsonify(status="ok"), 200

    # Inyección de variables globales en plantillas Jinja2
    @app.context_processor
    def inject_global_data():
        res = query_db("SELECT COUNT(*) as cnt FROM alertas WHERE leido = FALSE", one=True)
        alertas_no_leidas = res['cnt'] if res else 0

        return {
            'app_name': 'Credit Risk',
            'institucion': 'Caja Municipal de Ahorro y Crédito - CMAC',
            'database_provider': 'Supabase PostgreSQL' if Config.DATABASE_URL else 'SQLite local',
            'demo_mode': Config.DEMO_MODE,
            'current_user': {
                'id': session.get('user_id'),
                'nombre': session.get('user_name', 'Invitado'),
                'email': session.get('user_email', ''),
                'rol': session.get('user_role', 'Analista de créditos'),
                'cargo': session.get('user_cargo', 'Funcionario'),
                'agencia': session.get('user_agencia', 'Sede Central'),
                'avatar': session.get('user_avatar')
            },
            'alertas_pendientes_count': alertas_no_leidas,
            'today': date.today().isoformat(),
        }

    # Manejo elegante de errores
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', error_code=404, error_msg='La página solicitada no existe o ha sido reubicada.'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        current_app.logger.error("Error interno no controlado: %s", e)
        return render_template('base.html', error_code=500, error_msg='Ha ocurrido un error interno en el servidor. El equipo técnico ha sido notificado.'), 500

    # Iniciar escucha autónoma de Telegram en segundo plano (Webhook en Render o Polling resiliente)
    try:
        iniciar_demonio_telegram(app)
    except Exception as e_tg:
        app.logger.warning("No se pudo iniciar el demonio de Telegram: %s", e_tg)

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = Config.DEBUG
    print(f"\n" + "="*70)
    print("  Credit Risk - Sistema de Evaluación de Riesgo con IA")
    print("  Orientado a Cajas Municipales de Ahorro y Crédito del Perú")
    print(f"  Servidor local activo en: http://127.0.0.1:{port}")
    print("="*70 + "\n")
    app.run(host='0.0.0.0', port=port, debug=debug)
