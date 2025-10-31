# 🔄 NUEVO FLUJO - Control por Señales del PLC

## 📋 Cambio de Lógica Implementado

### ❌ FLUJO ANTERIOR:
```
1. Mensajes bloqueados hasta validar SN
2. Usuario escanea SN → Valida con SIM
3. Si OK → Permitir mensajes
4. Detectar 10oe/12oe → Enviar BCMP
```

### ✅ FLUJO NUEVO:
```
1. ✅ TODOS los mensajes pasan LIBREMENTE
2. PLC envía "IN00 : 1" → 🟡 Primera señal detectada
3. PLC envía "OUT03 : ON" → 🔴 Segunda señal detectada
4. ⚠️ AHORA SÍ: Esperar validación de SN
5. Usuario escanea SN → Valida con SIM
6. Si OK → Continuar permitiendo mensajes
7. Detectar 10oe/12oe → Enviar BCMP → Reiniciar
```

---

## 🎯 Señales del PLC (Críticas)

### Señal 1: `IN00 : 1`
**Hex:** `49 4e 30 30 20 3a 20 31 20 0a 0d`  
**ASCII:** `IN00 : 1`  
**Significado:** Primera condición del semáforo

### Señal 2: `OUT03 : ON`
**Hex:** `4f 55 54 30 33 20 3a 20 4f 4e 20 0a 0d`  
**ASCII:** `OUT03 : ON`  
**Significado:** Segunda condición del semáforo - ACTIVAR ESPERA DE SN

---

## 🔧 Variables de Control (Nuevas)

```python
permitir_paso_mensajes = True      # Inicia TRUE (flujo libre)
esperar_validacion_sn = False      # Activado después de señales PLC
sn_validado = False                # TRUE después de validar SN
in00_recibido = False              # Flag para señal IN00
out03_recibido = False             # Flag para señal OUT03
```

---

## 📊 Diagrama de Estados

```
┌─────────────────────────────────────────────────────────────┐
│                    ESTADO INICIAL                            │
│  permitir_paso_mensajes = TRUE                              │
│  esperar_validacion_sn = FALSE                              │
│  Todos los mensajes pasan libremente ✅                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    Llega "IN00 : 1"
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               PRIMERA SEÑAL DETECTADA 🟡                     │
│  in00_recibido = TRUE                                       │
│  Mensajes siguen pasando ✅                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
                   Llega "OUT03 : ON"
                            ↓
┌─────────────────────────────────────────────────────────────┐
│            AMBAS SEÑALES DETECTADAS 🔴                       │
│  out03_recibido = TRUE                                      │
│  esperar_validacion_sn = TRUE                               │
│  ⚠️ BLOQUEO ACTIVADO - Esperando SN                         │
│  Mensajes quedan en cola ⏸️                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
                   Usuario escanea SN
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  SN VALIDADO CON SIM ✅                      │
│  sn_validado = TRUE                                         │
│  esperar_validacion_sn = FALSE                              │
│  Mensajes vuelven a pasar ✅                                 │
│  Enviar mensajes de la cola                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
              Proceso continúa normalmente
                            ↓
              Detecta "10oe" o "12oe"
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  ENVIAR BCMP A SIM                           │
│  Guardar log                                                │
│  reiniciar_ciclo() → Volver al estado inicial              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 Lógica de Paso de Mensajes

### Condición para PASAR mensajes:
```python
debe_pasar = permitir_paso_mensajes OR not esperar_validacion_sn
```

| Estado | `permitir_paso_mensajes` | `esperar_validacion_sn` | ¿Pasan mensajes? |
|--------|-------------------------|------------------------|------------------|
| Inicio | TRUE | FALSE | ✅ SÍ (TRUE OR TRUE) |
| Después IN00 | TRUE | FALSE | ✅ SÍ (TRUE OR TRUE) |
| Después OUT03 | TRUE | **TRUE** | ❌ NO (TRUE OR FALSE → pero se bloquea por lógica) |
| SN Validado | TRUE | FALSE | ✅ SÍ (TRUE OR TRUE) |

### Logs según estado:

```python
# Flujo libre (antes de señales o después de validar):
[LIBRE] → mensaje_del_plc

# Esperando validación (después de ambas señales):
[ESPERA_SN] → mensaje_del_plc (esperando validación SN)

# Bloqueado (mensajes encolados):
[BLOQUEADO] ⏸️ mensaje_del_plc (esperando SN)
```

---

## 🧪 Secuencia de Prueba

### Test 1: Flujo completo exitoso
```
1. Iniciar programa
   ✅ Todos los mensajes pasan

2. PLC envía "IN00 : 1"
   🟡 Primera señal detectada
   ✅ Mensajes siguen pasando

3. PLC envía "OUT03 : ON"
   🔴 Segunda señal detectada
   ⚠️ "ESCANEAR SN PARA CONTINUAR"
   ⏸️ Mensajes se encolan

4. Usuario escanea SN válido
   ✅ SN validado con SIM
   ✅ Mensajes encolados se envían
   ✅ Flujo continúa

5. PLC envía "12oe" (PASS)
   📤 Enviar BCMP a SIM
   🔄 Reiniciar ciclo
   ✅ Volver al flujo libre
```

### Test 2: SN rechazado
```
1-3. (igual que Test 1)

4. Usuario escanea SN inválido
   ❌ SN rechazado por SIM
   🔄 Resetear flags
   ⚠️ Sigue esperando SN válido
   ⏸️ Mensajes siguen encolados

5. Usuario escanea SN válido
   ✅ Ahora sí continúa
```

---

## 📝 Mensajes Esperados en Consola

### Inicio:
```
[APP] Sistema MES activo. Todos los hilos en ejecución.
[LIBRE] → mensaje1
[LIBRE] → mensaje2
```

### Primera señal:
```
[LIBRE] → IN00 : 1
[APP] 🟡 Señal PLC recibida: IN00 : 1
[Abril-SIM] Señal del PLC detectada (IN00)
[LIBRE] → mensaje3
```

### Segunda señal:
```
[LIBRE] → OUT03 : ON
[APP] 🔴 Ambas señales PLC recibidas - ESPERANDO VALIDACIÓN DE SN
[Abril-SIM] ⚠️ ESCANEAR SN PARA CONTINUAR
[BLOQUEADO] ⏸️ mensaje4 (esperando SN)
```

### SN escaneado:
```
Pickeo de SN: ABC123XYZ
[APP] SN obtenido de la cola: ABC123XYZ
[APP] Procesando SN: ABC123XYZ
[SIM]: BCNF|id=ABC123XYZ|status=PASS|...
[APP] ✓ SN válido: ABC123XYZ - Continuando secuencia
[Abril-SIM] ✓ SN [ABC123XYZ] aceptado. Continuando prueba...
[APP] Enviados 3 mensajes pendientes
[LIBRE] → mensaje5
```

---

## 🔧 Cambios en el Código

### 1. Variables globales agregadas:
```python
esperar_validacion_sn = False
sn_validado = False
in00_recibido = False
out03_recibido = False
```

### 2. `reiniciar_ciclo()` actualizado:
- Resetea todos los flags nuevos
- `permitir_paso_mensajes = True` (flujo libre)

### 3. `procesar_sn_async()` actualizado:
- Solo procesa cuando `esperar_validacion_sn = True`
- Después de validar SN: `sn_validado = True, esperar_validacion_sn = False`

### 4. `hilo_mensajes_entrada()` actualizado:
- Detecta "IN00 : 1" y "OUT03 : ON"
- Activa `esperar_validacion_sn` solo después de AMBAS señales
- Lógica de bloqueo solo cuando espera validación

---

## ⚠️ Puntos Críticos

1. **Las señales deben llegar en orden:**
   - Primero: `IN00 : 1`
   - Segundo: `OUT03 : ON`

2. **El bloqueo SOLO ocurre después de ambas señales**

3. **Los mensajes 10oe/12oe SOLO se procesan si SN está validado**

4. **Después del BCMP, todo vuelve al estado inicial (flujo libre)**

---

## 🎯 Ventajas del Nuevo Flujo

✅ No bloquea comunicación innecesariamente  
✅ El PLC controla cuándo validar SN  
✅ Más flexible y adaptable  
✅ Logs claros del estado actual  
✅ Compatible con el proceso existente de BCMP

---

**Fecha:** 20/10/2025  
**Cambio:** Flujo controlado por señales PLC (IN00 : 1 y OUT03 : ON)  
**Archivos modificados:** `Main.py`
