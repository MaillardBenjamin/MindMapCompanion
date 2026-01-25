import enum


class NodeType(str, enum.Enum):
    idea = "idea"
    task = "task"
    note = "note"
    project = "project"
    event = "event"


class NodeStatus(str, enum.Enum):
    inbox = "inbox"
    clarify = "clarify"
    ready = "ready"
    doing = "doing"
    waiting = "waiting"
    done = "done"


class NodeSource(str, enum.Enum):
    ui = "ui"
    email = "email"
    api = "api"


class EdgeRelationType(str, enum.Enum):
    related = "related"
    parent = "parent"
    depends_on = "depends_on"
    mentions = "mentions"
    reference = "reference"


class CreatedBy(str, enum.Enum):
    human = "human"
    ai = "ai"


class ProposalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    applied = "applied"


class TriggerType(str, enum.Enum):
    email_received = "email_received"
    date_reached = "date_reached"
    cron = "cron"
    state_changed = "state_changed"
    manual = "manual"


class ActionType(str, enum.Enum):
    send_email = "send_email"
    draft_email = "draft_email"
    call_api = "call_api"
    update_node = "update_node"
    run_agent = "run_agent"
    notify = "notify"
    create_reminder = "create_reminder"
    reminder = "reminder"


class ActionMode(str, enum.Enum):
    auto = "auto"
    review = "review"
    manual = "manual"


class ExecutionStatus(str, enum.Enum):
    success = "success"
    failed = "failed"
    skipped = "skipped"
    needs_review = "needs_review"


class MailProvider(str, enum.Enum):
    gmail = "gmail"
    imap = "imap"


class EventType(str, enum.Enum):
    text_ingested = "TextIngested"
    email_received = "EmailReceived"
    date_reached = "DateReached"
    cron_tick = "CronTick"
    node_state_changed = "NodeStateChanged"
