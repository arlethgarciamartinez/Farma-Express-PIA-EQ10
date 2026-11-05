# Diagramas UML del código implementado (Mermaid; GitHub los dibuja directamente)

> Los diagramas de la U3 (`docs/u3/`) corresponden al diseño original de venta en mostrador con lotes.
> Estos describen **lo que está programado** en el incremento PIA (ver [BRD §9](BRD_final.md) y [ADR-005](adr/ADR-005-reconciliacion-modelo-pedido-vs-brd.md)).

## 1. Diagrama de clases — dominio
```mermaid
classDiagram
    direction LR
    class Pedido {
        <<Aggregate Root>>
        +id: str
        +estado: EstadoPedido
        +autorizado: bool
        +promocion_activa: bool
        +receta_fecha: date?
        +total() Dinero
        +validar(comprador, productos, hoy)
        +preparar(comprador, productos, hoy)
        +entregar(comprador)
        +cancelar()
        +agregar_linea(producto, cantidad)
        +extraer_eventos() list
    }
    class LineaPedido {
        <<Entity>>
        +recurso_id: str
        +precio_unitario: Dinero
        +cantidad: Cantidad
        +subtotal() Dinero
    }
    class Dinero { <<Value Object>> +monto: Decimal +moneda: str }
    class Cantidad { <<Value Object>> +valor: int }
    class Comprador { <<Entity>> +activo: bool +es_preferente: bool +ciudad: str }
    class Producto { <<Entity>> +precio: Dinero +stock: int +habilitado: bool +controlado: bool +descontar(cantidad) }
    class MaquinaDeEstados { +siguiente(estado, accion) EstadoPedido +acciones_permitidas(estado) }
    class EstadoPedido { <<enumeration>> CREADO VALIDADO PREPARADO ENTREGADO CANCELADO }
    class Specification { <<abstract>> +is_satisfied_by(contexto) bool +fallos(contexto) list }
    class AndSpecification
    class OrSpecification
    class NotSpecification
    class ContextoPedido { +pedido +comprador +productos +hoy }
    class EventoDeDominio { <<abstract>> +pedido_id +ocurrido_en }

    Pedido "1" *-- "0..*" LineaPedido
    LineaPedido --> Dinero
    LineaPedido --> Cantidad
    Pedido --> EstadoPedido
    Pedido ..> MaquinaDeEstados : usa
    Pedido ..> Specification : guardas (RN-01..05)
    Pedido ..> EventoDeDominio : emite
    Pedido ..> Comprador : referencia por id
    LineaPedido ..> Producto : referencia por id
    Specification <|-- AndSpecification
    Specification <|-- OrSpecification
    Specification <|-- NotSpecification
    Specification ..> ContextoPedido
    EventoDeDominio <|-- PedidoCreado
    EventoDeDominio <|-- PedidoValidado
    EventoDeDominio <|-- PedidoPreparado
    EventoDeDominio <|-- PedidoEntregado
    EventoDeDominio <|-- PedidoCancelado
```

## 2. Capas y dependencias (ADR-001)
```mermaid
flowchart LR
    API["api<br/>FastAPI · schemas · errores"] --> APP["application<br/>ServicioPedidos · puertos"]
    APP --> DOM["domain<br/>Pedido · Specifications · estados · eventos"]
    INF["infrastructure<br/>SQLAlchemy · repos · bus · CSV"] --> APP
    INF --> DOM
    INF -.-> DB[("PostgreSQL")]
```
La regla (dominio no importa a nadie) la verifica `tests/test_arquitectura.py`.

## 3. Secuencia — validar un pedido (caso feliz y rechazo 422)
```mermaid
sequenceDiagram
    actor C as Cajero
    participant R as Router (api)
    participant S as ServicioPedidos
    participant U as UnidadDeTrabajo (SQL)
    participant P as Pedido (domain)
    participant B as Bus de eventos
    C->>R: POST /pedidos/{id}/validar
    R->>S: validar(id)
    S->>U: obtener pedido, comprador, productos
    S->>P: validar(comprador, productos, hoy)
    P->>P: MaquinaDeEstados.siguiente(CREADO, validar)
    alt transición ilegal
        P-->>R: TransicionInvalida → 409
    else reglas incumplidas (PUEDE_VALIDARSE)
        P-->>R: ReglaDeNegocioIncumplida → 422 + reglas_incumplidas
    else cumple
        P->>P: estado = VALIDADO · registra PedidoValidado
        S->>U: guardar pedido + evento · commit
        S->>B: publicar(PedidoValidado) (sólo tras commit)
        R-->>C: 200 {estado: VALIDADO}
    end
```

## 4. Secuencia — preparar y entregar (descuento de existencia)
```mermaid
sequenceDiagram
    actor A as Almacén
    participant S as ServicioPedidos
    participant P as Pedido
    participant X as Producto
    A->>S: preparar(id)
    S->>P: preparar(comprador, productos)
    P->>P: guarda PUEDE_PREPARARSE (habilitado ∧ existencia)
    loop cada línea
        P->>X: descontar(cantidad)
    end
    P->>P: estado = PREPARADO · evento PedidoPreparado
    S->>S: guardar productos + pedido + eventos · commit · publicar
    A->>S: entregar(id)
    S->>P: entregar(comprador)
    P->>P: estado = ENTREGADO · PedidoEntregado(beneficio_referencia = RN-02)
```

## 5. Máquina de estados
Ver el diagrama de estados en [BRD §9.4](BRD_final.md) (RN-06) y [ADR-003](adr/ADR-003-maquina-de-estados-por-tabla.md).
