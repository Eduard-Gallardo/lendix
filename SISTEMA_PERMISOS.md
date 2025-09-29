# Sistema de Permisos de Ambientes - LibraTech

## Descripción

El sistema de permisos permite que los instructores controlen qué ambientes pueden usar los aprendices para solicitar préstamos de implementos. Los aprendices solo pueden solicitar préstamos en ambientes donde su instructor haya habilitado los permisos.

## Funcionalidades Implementadas

### 1. Tipos de Usuario
- **Admin**: Acceso completo al sistema (Eduard@gmail.com)
- **Instructor**: Puede gestionar permisos de ambientes y asignar aprendices
- **Aprendiz**: Puede solicitar préstamos solo en ambientes habilitados por su instructor

### 2. Gestión de Permisos
- Los instructores pueden habilitar/deshabilitar ambientes para préstamos
- Los instructores pueden asignar aprendices a ambientes específicos
- Los aprendices solo pueden solicitar préstamos en ambientes donde:
  - Están asignados a un instructor
  - El instructor ha habilitado los permisos para ese ambiente

### 3. Base de Datos

#### Nuevas Tablas:
- `permisos_ambientes`: Controla qué ambientes están habilitados por cada instructor
- `asignaciones_aprendices`: Relaciona aprendices con instructores en ambientes específicos

#### Tabla `usuarios` actualizada:
- Agregado campo `tipo_usuario` (aprendiz/instructor)
- Agregado campo `activo` (boolean)
- Agregado campo `fecha_registro` (timestamp)

### 4. Interfaz de Usuario

#### Para Instructores:
- Panel de gestión de permisos accesible desde el menú de usuario
- Formulario para configurar permisos de ambientes
- Formulario para asignar aprendices a ambientes
- Vista de permisos configurados
- Vista de aprendices asignados

#### Para Aprendices:
- Restricciones automáticas al solicitar préstamos
- Mensajes informativos cuando no tienen permisos
- Solo pueden ver y usar ambientes habilitados por su instructor

## Flujo de Trabajo

### 1. Registro de Usuarios
1. Los usuarios se registran seleccionando su tipo (aprendiz/instructor)
2. El sistema guarda el tipo de usuario en la base de datos

### 2. Configuración de Permisos (Instructores)
1. El instructor accede a "Gestionar Permisos" desde su perfil
2. Selecciona un ambiente y habilita/deshabilita los préstamos
3. Asigna aprendices a ambientes específicos

### 3. Solicitud de Préstamos (Aprendices)
1. El aprendiz intenta solicitar un préstamo
2. El sistema verifica:
   - Si el aprendiz está asignado a un instructor en ese ambiente
   - Si el instructor ha habilitado los permisos para ese ambiente
3. Si tiene permisos: procede con el préstamo
4. Si no tiene permisos: muestra mensaje de error explicativo

## Ambientes Disponibles

El sistema incluye 19 ambientes predefinidos:
- Aulas: 101, 102, 103, 104, 105
- Laboratorios: Sistemas, Redes, Electrónica
- Talleres: Mecánica, Soldadura, Carpintería
- Espacios comunes: Biblioteca, Sala de Estudio, Auditorio, etc.

## API Endpoints

### Para Instructores:
- `GET /admin/gestion_permisos` - Panel de gestión
- `POST /admin/configurar_permiso_ambiente` - Configurar permisos
- `POST /admin/asignar_aprendiz` - Asignar aprendices
- `GET /admin/obtener_aprendices_disponibles` - Lista de aprendices

### Para Verificación:
- `GET /admin/verificar_permiso_prestamo/<ambiente>` - Verificar permisos

## Seguridad

- Solo instructores y admins pueden gestionar permisos
- Los aprendices no pueden modificar sus propios permisos
- Verificación de permisos en cada solicitud de préstamo
- Validación de tipos de usuario en todas las operaciones

## Instalación y Uso

1. **Ejecutar la aplicación**:
   ```bash
   python app.py
   ```

2. **Registrar usuarios**:
   - Crear cuentas de instructores y aprendices
   - Seleccionar el tipo de usuario apropiado

3. **Configurar permisos**:
   - Los instructores acceden a "Gestionar Permisos"
   - Configuran qué ambientes están habilitados
   - Asignan aprendices a ambientes específicos

4. **Usar el sistema**:
   - Los aprendices pueden solicitar préstamos solo en ambientes habilitados
   - El sistema valida automáticamente los permisos

## Archivos Modificados/Creados

### Nuevos Archivos:
- `utils/permisos.py` - Lógica de permisos
- `templates/admin/gestion_permisos.html` - Interfaz de gestión
- `SISTEMA_PERMISOS.md` - Esta documentación

### Archivos Modificados:
- `utils/db.py` - Nuevas tablas y campos
- `routes/admin.py` - Rutas de gestión de permisos
- `routes/catalogo.py` - Verificación de permisos en préstamos
- `routes/registro.py` - Soporte para tipo de usuario
- `routes/login.py` - Manejo de roles
- `templates/views/registro.html` - Selector de tipo de usuario
- `templates/base.html` - Enlace de gestión para instructores

## Próximas Mejoras

- Notificaciones automáticas a aprendices cuando cambien los permisos
- Historial de cambios en permisos
- Reportes de uso por ambiente
- Integración con calendario académico
- Permisos temporales con fechas de inicio y fin
