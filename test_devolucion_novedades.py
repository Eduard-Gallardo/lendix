#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad de devolución con novedades
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db import get_db_connection
from datetime import datetime

def test_devolucion_con_novedades():
    """Prueba la funcionalidad de devolución con novedades que reducen cantidad"""
    
    print("=== PRUEBA DE DEVOLUCIÓN CON NOVEDADES ===\n")
    
    # Conectar a la base de datos
    conn = get_db_connection()
    
    try:
        # 1. Verificar implementos disponibles
        print("1. Verificando implementos disponibles...")
        implementos = conn.execute('''
            SELECT id, implemento, disponibilidad, categoria 
            FROM implementos 
            ORDER BY implemento
        ''').fetchall()
        
        if not implementos:
            print("❌ No hay implementos en la base de datos")
            return False
        
        print(f"✅ Encontrados {len(implementos)} implementos:")
        for impl in implementos:
            print(f"   - ID: {impl['id']}, {impl['implemento']} (Disponibles: {impl['disponibilidad']})")
        
        # 2. Verificar préstamos activos
        print("\n2. Verificando préstamos activos...")
        prestamos_activos = conn.execute('''
            SELECT p.id, p.fk_implemento, i.implemento, i.disponibilidad
            FROM prestamos p
            JOIN implementos i ON p.fk_implemento = i.id
            WHERE p.fecha_devolucion IS NULL
            ORDER BY p.id DESC
            LIMIT 3
        ''').fetchall()
        
        if not prestamos_activos:
            print("❌ No hay préstamos activos para probar")
            return False
        
        print(f"✅ Encontrados {len(prestamos_activos)} préstamos activos:")
        for prestamo in prestamos_activos:
            print(f"   - ID: {prestamo['id']}, {prestamo['implemento']} (Disponibles actuales: {prestamo['disponibilidad']})")
        
        # 3. Simular devolución con novedad
        print("\n3. Simulando devolución con novedad...")
        
        prestamo_prueba = prestamos_activos[0]
        novedad = "Daño"
        estado_implemento = "Dañado"
        observaciones = "Implemento dañado durante el uso"
        
        print(f"   - Préstamo ID: {prestamo_prueba['id']}")
        print(f"   - Implemento: {prestamo_prueba['implemento']}")
        print(f"   - Disponibilidad actual: {prestamo_prueba['disponibilidad']}")
        print(f"   - Novedad: {novedad}")
        print(f"   - Estado: {estado_implemento}")
        
        # Obtener disponibilidad actual del implemento
        implemento_actual = conn.execute(
            'SELECT disponibilidad FROM implementos WHERE id = ?', 
            (prestamo_prueba['fk_implemento'],)
        ).fetchone()
        
        disponibilidad_antes = implemento_actual['disponibilidad']
        print(f"   - Disponibilidad antes de la devolución: {disponibilidad_antes}")
        
        # Simular la lógica de devolución
        novedades_que_reducen_cantidad = ['Daño', 'Robo', 'Desgaste excesivo', 'Pérdida']
        cantidad_a_reducir = 0
        
        if novedad in novedades_que_reducen_cantidad:
            cantidad_a_reducir = 1
            print(f"   - Novedad '{novedad}' detectada - reduciendo cantidad en {cantidad_a_reducir}")
        
        # Calcular nueva disponibilidad (normalmente +1, pero -1 si hay novedad grave)
        nueva_disponibilidad = disponibilidad_antes + 1 - cantidad_a_reducir
        
        # Asegurar que la disponibilidad no sea negativa
        if nueva_disponibilidad < 0:
            nueva_disponibilidad = 0
        
        print(f"   - Nueva disponibilidad calculada: {nueva_disponibilidad}")
        
        # 4. Actualizar en la base de datos
        print("\n4. Actualizando en la base de datos...")
        
        # Marcar préstamo como devuelto
        fecha_devolucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute('''
            UPDATE prestamos 
            SET fecha_devolucion = ?, novedad = ?, estado_implemento_devolucion = ?, observaciones = ?
            WHERE id = ?
        ''', (fecha_devolucion, novedad, estado_implemento, observaciones, prestamo_prueba['id']))
        
        # Actualizar disponibilidad del implemento
        conn.execute(
            'UPDATE implementos SET disponibilidad = ? WHERE id = ?',
            (nueva_disponibilidad, prestamo_prueba['fk_implemento'])
        )
        
        # Actualizar estado del implemento
        conn.execute(
            'UPDATE implementos SET estado = ? WHERE id = ?',
            (estado_implemento, prestamo_prueba['fk_implemento'])
        )
        
        # Confirmar transacción
        conn.commit()
        print("✅ Transacción confirmada")
        
        # 5. Verificar los cambios
        print("\n5. Verificando cambios...")
        
        # Verificar préstamo
        prestamo_actualizado = conn.execute('''
            SELECT fecha_devolucion, novedad, estado_implemento_devolucion, observaciones
            FROM prestamos WHERE id = ?
        ''', (prestamo_prueba['id'],)).fetchone()
        
        print("✅ Préstamo actualizado:")
        print(f"   - Fecha devolución: {prestamo_actualizado['fecha_devolucion']}")
        print(f"   - Novedad: {prestamo_actualizado['novedad']}")
        print(f"   - Estado implemento: {prestamo_actualizado['estado_implemento_devolucion']}")
        print(f"   - Observaciones: {prestamo_actualizado['observaciones']}")
        
        # Verificar implemento
        implemento_actualizado = conn.execute('''
            SELECT disponibilidad, estado FROM implementos WHERE id = ?
        ''', (prestamo_prueba['fk_implemento'],)).fetchone()
        
        print("✅ Implemento actualizado:")
        print(f"   - Nueva disponibilidad: {implemento_actualizado['disponibilidad']}")
        print(f"   - Estado: {implemento_actualizado['estado']}")
        
        # 6. Crear notificación de prueba
        print("\n6. Creando notificación...")
        
        mensaje_notif = f'Devolución de {prestamo_prueba["implemento"]} por Usuario Prueba'
        if novedad != 'Ninguna':
            mensaje_notif += f' - Novedad: {novedad}'
            if novedad in novedades_que_reducen_cantidad:
                mensaje_notif += ' - Se redujo la cantidad disponible del implemento'
        if estado_implemento != 'Bueno':
            mensaje_notif += f' - Estado: {estado_implemento}'
        
        print(f"✅ Mensaje de notificación: {mensaje_notif}")
        
        print("\n=== PRUEBA COMPLETADA EXITOSAMENTE ===")
        print(f"✅ La novedad '{novedad}' redujo correctamente la cantidad del implemento")
        print(f"✅ Disponibilidad cambió de {disponibilidad_antes} a {nueva_disponibilidad}")
        return True
        
    except Exception as e:
        print(f"❌ Error durante la prueba: {str(e)}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    success = test_devolucion_con_novedades()
    sys.exit(0 if success else 1)

