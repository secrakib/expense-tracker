from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

from typing import Literal, Optional
from typing_extensions import TypedDict

from pydantic import BaseModel, field_validator
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from rapidfuzz import process as fuzz_process

from backend.src.feature.filter_and_show import filter_expenses
from backend.src.feature.add_values import add_values
from backend.src.feature.update_values import update_values
from backend.src.feature.delete_record import delete_record
from backend.src.feature.get_categories import get_categories

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_NAME      = "llama-3.3-70b-versatile"
DB_LOCATION     = "backend/database/database.db"
MAX_RETRIES     = 3
FUZZY_THRESHOLD = 90

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = SystemMessage(content="""
You are an expense tracking assistant. Your only job is to help users
manage their personal expenses — adding, viewing, updating, and deleting records.

Rules:
- Only respond to expense-related requests. Politely decline anything else.
- Always extract: category (short, lowercase), amount (number), date (YYYY-MM-DD).
- When classifying intent, never guess — use 'clarify' if unsure.
- Be concise and friendly. No markdown, no long explanations.
- Categories should be simple: food, transport, rent, entertainment, etc.
- Amounts are always positive numbers.
- If the user mentions a currency (taka, dollar, pound etc.), extract just the number.
""")

# ── LLM ───────────────────────────────────────────────────────────────────────
llm = ChatGroq(model=MODEL_NAME, temperature=0)

# ── State ─────────────────────────────────────────────────────────────────────
# All intermediate values must live in state so they survive across nodes.
class AgentState(TypedDict):
    messages: list
    username: str
    intent: str

    # shared across all flows
    available_categories: list[str]
    pending_action: str
    confirmed: bool

    # add / update / delete share these staging fields
    stage_category: str | None       # raw category from LLM
    stage_expense: float | None
    stage_date: str | None
    stage_id: int | None             # update only

    # fuzzy resolution
    fuzzy_input: str | None          # what the user typed
    fuzzy_matches: list              # list of (name, score) tuples
    resolved_category: str | None   # final category after fuzzy resolution

    # view-specific filters
    view_min: float | None
    view_max: float | None

    # retry counter for missing-fields loops
    retry_count: int


# ── Pydantic models ───────────────────────────────────────────────────────────
class IntentResult(BaseModel):
    intent: Literal["view", "add", "update", "delete", "clarify"]
    reason: str

class ViewParams(BaseModel):
    category: Optional[str] = None
    date: Optional[str] = None
    min_expense: Optional[float] = None
    max_expense: Optional[float] = None

    @field_validator("min_expense", "max_expense", mode="before")
    @classmethod
    def coerce_floats(cls, v):
        try: return float(v) if v is not None else None
        except (ValueError, TypeError): return None

class AddParams(BaseModel):
    category: Optional[str] = None
    expense: Optional[float] = None
    date: Optional[str] = None

    @field_validator("expense", mode="before")
    @classmethod
    def coerce_expense(cls, v):
        try: return float(v) if v is not None else None
        except (ValueError, TypeError): return None

class UpdateParams(BaseModel):
    id: Optional[int] = None
    category: Optional[str] = None
    expense: Optional[float] = None
    date: Optional[str] = None

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, v):
        try: return int(v) if v is not None else None
        except (ValueError, TypeError): return None

    @field_validator("expense", mode="before")
    @classmethod
    def coerce_expense(cls, v):
        try: return float(v) if v is not None else None
        except (ValueError, TypeError): return None

    @field_validator("category", "date", mode="before")
    @classmethod
    def coerce_str(cls, v):
        if not isinstance(v, str): return None
        cleaned = v.strip().lower()
        # reject placeholder values the LLM sometimes returns
        return None if cleaned in ("clarify", "unknown", "n/a", "none", "") else v

class DeleteParams(BaseModel):
    category: Optional[str] = None
    date: Optional[str] = None
    min_expense: Optional[float] = None
    max_expense: Optional[float] = None

    @field_validator("min_expense", "max_expense", mode="before")
    @classmethod
    def coerce_floats(cls, v):
        try: return float(v) if v is not None else None
        except (ValueError, TypeError): return None


# ── Utilities ─────────────────────────────────────────────────────────────────
def fuzzy_match(input_category: str, existing: list[str]) -> list[tuple[str, int]]:
    if not existing:
        return []
    results = fuzz_process.extract(input_category.lower().strip(),
                                   [c.lower().strip() for c in existing])
    return [(name, score) for name, score, _ in results if score >= FUZZY_THRESHOLD]

def fmt_expenses(rows: list[dict]) -> str:
    if not rows:
        return "(none)"
    lines = ["  ID | Category     | Amount  | Date", "  " + "-" * 42]
    for r in rows:
        lines.append(f"  {r['id']:>3} | {r['category']:<12} | {r['expense']:>7.2f} | {r['date']}")
    return "\n".join(lines)

def say(msg: str):
    print(f"\n🤖 {msg}\n")

def _load_categories(state: AgentState) -> list[str]:
    try:
        return get_categories(DB_LOCATION, state["username"])
    except Exception:
        return []


# ═════════════════════════════════════════════════════════════════════════════
# SHARED NODES
# ═════════════════════════════════════════════════════════════════════════════

def intent_router_node(state: AgentState) -> AgentState:
    """Classify intent from last user message."""
    user_msg = state["messages"][-1]["content"]
    extractor = llm.with_structured_output(IntentResult)
    result: IntentResult = extractor.invoke([
        SYSTEM_PROMPT,
        HumanMessage(content=
            f"Classify the user's intent for an expense tracker app.\n"
            f"Intents: view, add, update, delete, clarify (if ambiguous or off-topic).\n"
            f"User said: {user_msg}"
        )
    ])
    if result.intent == "clarify":
        say(f"Could you clarify? {result.reason}")
        # interrupt here is fine — this node has no costly work before it
        new_input = interrupt("Waiting for clarification")
        return {**state,
                "intent": "clarify",
                "messages": state["messages"] + [{"role": "user", "content": new_input}]}
    return {**state, "intent": result.intent}


def fuzzy_node(state: AgentState) -> AgentState:
    """
    Generic fuzzy-approval node (one interrupt, nothing costly before it).
    Reads:  state.fuzzy_input, state.fuzzy_matches
    Writes: state.resolved_category
    """
    matches = state.get("fuzzy_matches", [])
    fuzzy_input = state.get("fuzzy_input", "")

    if not matches:
        # No close match — use whatever the user typed as-is
        return {**state, "resolved_category": fuzzy_input.lower().strip() if fuzzy_input else None}

    if len(matches) == 1:
        matched, score = matches[0]
        say(f'Did you mean "{matched}" (similarity {score})? Reply "yes" to use it or type a different category.')
    else:
        options = "\n".join(f"  {i+1}. {m} ({s}%)" for i, (m, s) in enumerate(matches))
        say(f'Found similar categories:\n{options}\nType a number to pick one, or type your own.')

    answer = interrupt("Fuzzy approval")

    if len(matches) == 1:
        matched = matches[0][0]
        resolved = matched if answer.strip().lower() in ("yes", "y") else answer.strip().lower()
    else:
        try:
            idx = int(answer.strip()) - 1
            resolved = matches[idx][0] if 0 <= idx < len(matches) else answer.strip().lower()
        except ValueError:
            resolved = answer.strip().lower()

    return {**state, "resolved_category": resolved}


def confirm_node(state: AgentState) -> AgentState:
    """Generic confirmation node — one interrupt, nothing before it."""
    say(f"About to do:\n  {state['pending_action']}\nConfirm? (yes/no)")
    answer = interrupt("Confirmation")
    return {**state, "confirmed": answer.strip().lower() in ("yes", "y")}


# ═════════════════════════════════════════════════════════════════════════════
# VIEW PIPELINE:  view_extract → (view_fuzzy?) → view_execute
# ═════════════════════════════════════════════════════════════════════════════

def view_extract_node(state: AgentState) -> AgentState:
    cats = _load_categories(state)
    user_msg = state["messages"][-1]["content"]
    extractor = llm.with_structured_output(ViewParams)
    params: ViewParams = extractor.invoke([
        SYSTEM_PROMPT,
        HumanMessage(content=
            f"Extract view/filter parameters (category, date, min_expense, max_expense).\n"
            f"Available categories: {cats}\n"
            f"User said: {user_msg}"
        )
    ])
    matches = fuzzy_match(params.category, cats) if params.category else []
    return {**state,
            "available_categories": cats,
            "stage_category": params.category,
            "stage_date": params.date,
            "view_min": params.min_expense,
            "view_max": params.max_expense,
            "fuzzy_input": params.category,
            "fuzzy_matches": matches,
            "resolved_category": params.category}  # default if no fuzzy


def view_execute_node(state: AgentState) -> AgentState:
    cat = state.get("resolved_category")
    try:
        rows = filter_expenses(DB_LOCATION, state["username"], cat,
                               state.get("stage_date"),
                               state.get("view_min"),
                               state.get("view_max"))
        if rows:
            say(f"Found {len(rows)} expense(s):\n{fmt_expenses(rows)}")
        else:
            say("No expenses found matching your filters.")
    except Exception:
        say("Something went wrong fetching your expenses. Please try again.")
    return {**state, "intent": ""}


# ═════════════════════════════════════════════════════════════════════════════
# ADD PIPELINE:  add_extract → (add_fuzzy?) → add_missing → add_confirm → add_execute
# ═════════════════════════════════════════════════════════════════════════════

def add_extract_node(state: AgentState) -> AgentState:
    cats = _load_categories(state)
    user_msg = state["messages"][-1]["content"]
    extractor = llm.with_structured_output(AddParams)
    params: AddParams = extractor.invoke([
        SYSTEM_PROMPT,
        HumanMessage(content=
            f"Extract expense details (category, amount as a number, date as YYYY-MM-DD).\n"
            f"Existing categories: {cats}\n"
            f"User said: {user_msg}"
        )
    ])

    # If no category extracted, ask LLM for a suggestion and store it
    category = params.category
    if not category:
        category = llm.invoke([
            SYSTEM_PROMPT,
            HumanMessage(content=
                f"Suggest a short expense category (1-2 words, lowercase).\n"
                f"Existing: {cats}\n"
                f"User said: {user_msg}\n"
                f"Reply with the category name only."
            )
        ]).content.strip().lower()

    matches = fuzzy_match(category, cats) if category else []
    return {**state,
            "available_categories": cats,
            "stage_category": category,
            "stage_expense": params.expense,
            "stage_date": params.date,
            "fuzzy_input": category,
            "fuzzy_matches": matches,
            "resolved_category": category,   # default if no fuzzy
            "retry_count": 0}


def add_category_suggest_node(state: AgentState) -> AgentState:
    """
    Only reached when add_extract found no category in the message at all
    (stage_category was set via LLM suggestion). Ask user to approve suggestion.
    This is a separate interrupt so it never replays with the extract work.
    """
    suggestion = state.get("stage_category", "")
    say(f'I suggest category "{suggestion}". Type "yes" to accept or enter your own.')
    answer = interrupt("Category suggestion approval")
    resolved = suggestion if answer.strip().lower() in ("yes", "y") else answer.strip().lower()
    return {**state, "resolved_category": resolved}


def add_missing_node(state: AgentState) -> AgentState:
    """Ask for amount/date if missing. One interrupt, loops via graph edge."""
    expense  = state.get("stage_expense")
    exp_date = state.get("stage_date")

    if expense is not None and exp_date is not None:
        return state  # nothing missing, pass through

    if state.get("retry_count", 0) >= MAX_RETRIES:
        say("I wasn't able to complete this — please try rephrasing your request.")
        return {**state, "intent": "abort"}

    missing = []
    if expense is None:  missing.append("amount")
    if exp_date is None: missing.append("date (YYYY-MM-DD)")
    say(f"Please provide: {', '.join(missing)}")
    extra = interrupt("Missing add fields")

    extractor = llm.with_structured_output(AddParams)
    fill: AddParams = extractor.invoke([
        SYSTEM_PROMPT,
        HumanMessage(content=f"Extract expense amount and/or date (YYYY-MM-DD) from: {extra}")
    ])
    return {**state,
            "stage_expense": fill.expense if fill.expense is not None else expense,
            "stage_date":    fill.date    if fill.date    is not None else exp_date,
            "retry_count":   state.get("retry_count", 0) + 1}


def add_confirm_node(state: AgentState) -> AgentState:
    cat     = state.get("resolved_category", "?")
    expense = state.get("stage_expense", 0)
    date    = state.get("stage_date", "?")
    return {**state,
            "pending_action": f"Add expense: {cat} | {expense:.2f} | {date}"}
    # confirm_node runs next (shared)


def add_execute_node(state: AgentState) -> AgentState:
    if not state.get("confirmed"):
        say("Cancelled.")
        return {**state, "intent": ""}
    try:
        result = add_values(state["username"],
                            state["resolved_category"],
                            state["stage_expense"],
                            state["stage_date"],
                            DB_LOCATION)
        say(result["message"])
    except ValueError:
        say("Could not add expense. Please try again.")
    return {**state, "intent": ""}


# ═════════════════════════════════════════════════════════════════════════════
# UPDATE PIPELINE:  update_extract → update_id_missing? → (update_fuzzy?) →
#                   update_fields_missing? → update_confirm → update_execute
# ═════════════════════════════════════════════════════════════════════════════

def update_extract_node(state: AgentState) -> AgentState:
    cats = _load_categories(state)
    user_msg = state["messages"][-1]["content"]

    # If message is too vague, skip LLM extraction entirely
    extractor = llm.with_structured_output(UpdateParams)
    params: UpdateParams = extractor.invoke([
        SYSTEM_PROMPT,
        HumanMessage(content=
            f"Extract update parameters from the user message.\n"
            f"Rules:\n"
            f"- 'id' must be an integer or null (never a string)\n"
            f"- 'expense' must be a number or null (never a string)\n"
            f"- 'category' must be a short word or null\n"
            f"- 'date' must be YYYY-MM-DD or null\n"
            f"- If a field is not mentioned, set it to null\n"
            f"User said: {user_msg}"
        )
    ])
    matches = fuzzy_match(params.category, cats) if params.category else []
    return {**state,
            "available_categories": cats,
            "stage_id":       params.id,
            "stage_category": params.category,
            "stage_expense":  params.expense,
            "stage_date":     params.date,
            "fuzzy_input":    params.category,
            "fuzzy_matches":  matches,
            "resolved_category": params.category,
            "retry_count": 0}


def update_id_node(state: AgentState) -> AgentState:
    """Ask for ID if missing. One interrupt."""
    if state.get("stage_id") is not None:
        return state

    if state.get("retry_count", 0) >= MAX_RETRIES:
        say("I wasn't able to complete this — please try rephrasing your request.")
        return {**state, "intent": "abort"}

    rows = filter_expenses(DB_LOCATION, state["username"])
    say(f"Which expense do you want to update?\n{fmt_expenses(rows)}\nProvide the ID:")
    answer = interrupt("Update ID")

    extractor = llm.with_structured_output(UpdateParams)
    refill: UpdateParams = extractor.invoke([
        SYSTEM_PROMPT,
        HumanMessage(content=f"Extract the expense ID from: {answer}")
    ])
    return {**state,
            "stage_id":    refill.id,
            "retry_count": state.get("retry_count", 0) + 1}


def update_fields_node(state: AgentState) -> AgentState:
    cat     = state.get("resolved_category")
    expense = state.get("stage_expense")
    date    = state.get("stage_date")

    if any([cat, expense, date]):
        return state

    if state.get("retry_count", 0) >= MAX_RETRIES:
        say("I wasn't able to complete this — please try rephrasing your request.")
        return {**state, "intent": "abort"}

    say("What would you like to change? Please provide the new value(s), e.g. 'amount 150', 'date 2025-01-01', or 'category food'")
    answer = interrupt("Update fields")

    extractor = llm.with_structured_output(UpdateParams)
    refill: UpdateParams = extractor.invoke([
        SYSTEM_PROMPT,
        HumanMessage(content=
            f"Extract fields to update (category, expense as a number, date as YYYY-MM-DD).\n"
            f"Rules:\n"
            f"- 'expense' must be an actual number (e.g. 150.0), never a word like 'amount'\n"
            f"- If only a field name is given without a value, set it to null\n"
            f"- 'date' must be YYYY-MM-DD or null\n"
            f"From: {answer}"
        )
    ])
    cats = state.get("available_categories", [])
    new_cat = refill.category
    matches = fuzzy_match(new_cat, cats) if new_cat else []
    return {**state,
            "stage_category":    new_cat or cat,
            "stage_expense":     refill.expense or expense,
            "stage_date":        refill.date or date,
            "fuzzy_input":       new_cat,
            "fuzzy_matches":     matches,
            "resolved_category": new_cat or cat,
            "retry_count":       state.get("retry_count", 0) + 1}


def update_confirm_node(state: AgentState) -> AgentState:
    changes = []
    if state.get("resolved_category"): changes.append(f"category → {state['resolved_category']}")
    if state.get("stage_expense"):     changes.append(f"amount → {state['stage_expense']:.2f}")
    if state.get("stage_date"):        changes.append(f"date → {state['stage_date']}")
    return {**state,
            "pending_action": f"Update expense #{state['stage_id']}: {', '.join(changes)}"}


def update_execute_node(state: AgentState) -> AgentState:
    if not state.get("confirmed"):
        say("Cancelled.")
        return {**state, "intent": ""}
    try:
        result = update_values(DB_LOCATION,
                               state["stage_id"],
                               state["username"],
                               state.get("resolved_category"),
                               state.get("stage_expense"),
                               state.get("stage_date"))
        say(f"Updated expense #{result['updated_id']}. Changes: {result['changes']}")
    except ValueError:
        say(f"Could not find expense #{state['stage_id']} for your account.")
    return {**state, "intent": ""}


# ═════════════════════════════════════════════════════════════════════════════
# DELETE PIPELINE:  delete_extract → delete_filter_missing? → (delete_fuzzy?) →
#                   delete_confirm → delete_execute
# ═════════════════════════════════════════════════════════════════════════════

def delete_extract_node(state: AgentState) -> AgentState:
    cats = _load_categories(state)
    user_msg = state["messages"][-1]["content"]
    extractor = llm.with_structured_output(DeleteParams)
    params: DeleteParams = extractor.invoke([
        SYSTEM_PROMPT,
        HumanMessage(content=
            f"Extract delete filter parameters (category, date, min_expense, max_expense).\n"
            f"Available categories: {cats}\n"
            f"User said: {user_msg}"
        )
    ])
    matches = fuzzy_match(params.category, cats) if params.category else []
    return {**state,
            "available_categories": cats,
            "stage_category": params.category,
            "stage_date":     params.date,
            "view_min":       params.min_expense,
            "view_max":       params.max_expense,
            "fuzzy_input":    params.category,
            "fuzzy_matches":  matches,
            "resolved_category": params.category,
            "retry_count": 0}


def delete_filter_node(state: AgentState) -> AgentState:
    """Ask for at least one filter if none given. One interrupt."""
    cat  = state.get("resolved_category")
    date = state.get("stage_date")
    mn   = state.get("view_min")
    mx   = state.get("view_max")

    if any([cat, date, mn is not None, mx is not None]):
        return state

    if state.get("retry_count", 0) >= MAX_RETRIES:
        say("I wasn't able to complete this — please try rephrasing your request.")
        return {**state, "intent": "abort"}

    say("Please provide at least one filter (category, date, min/max amount):")
    answer = interrupt("Delete filter")

    cats = state.get("available_categories", [])
    extractor = llm.with_structured_output(DeleteParams)
    params: DeleteParams = extractor.invoke([
        SYSTEM_PROMPT,
        HumanMessage(content=f"Extract delete filter parameters from: {answer}")
    ])
    matches = fuzzy_match(params.category, cats) if params.category else []
    return {**state,
            "stage_category": params.category,
            "stage_date":     params.date,
            "view_min":       params.min_expense,
            "view_max":       params.max_expense,
            "fuzzy_input":    params.category,
            "fuzzy_matches":  matches,
            "resolved_category": params.category,
            "retry_count": state.get("retry_count", 0) + 1}


def delete_confirm_node(state: AgentState) -> AgentState:
    try:
        preview = filter_expenses(DB_LOCATION, state["username"],
                                  state.get("resolved_category"),
                                  state.get("stage_date"),
                                  state.get("view_min"),
                                  state.get("view_max"))
    except Exception:
        say("Something went wrong fetching expenses. Please try again.")
        return {**state, "intent": "abort"}

    if not preview:
        say("No matching expenses found.")
        return {**state, "intent": "abort"}

    return {**state,
            "pending_action": f"Delete {len(preview)} expense(s):\n{fmt_expenses(preview)}"}


def delete_execute_node(state: AgentState) -> AgentState:
    if not state.get("confirmed"):
        say("Cancelled.")
        return {**state, "intent": ""}
    try:
        result = delete_record(DB_LOCATION, state["username"],
                               state.get("resolved_category"),
                               state.get("stage_date"),
                               state.get("view_min"),
                               state.get("view_max"))
        say(f"{result['message']} IDs: {result['deleted_ids']}")
    except Exception:
        say("Could not delete expenses. Please try again.")
    return {**state, "intent": ""}


# ═════════════════════════════════════════════════════════════════════════════
# ROUTING HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def route_intent(state: AgentState) -> str:
    intent = state.get("intent", "")
    if intent in ("clarify", ""):
        return "router"
    return intent                  # "view" | "add" | "update" | "delete"

def route_abort(state: AgentState) -> str:
    """After nodes that can set intent='abort', redirect to END."""
    return "end" if state.get("intent") == "abort" else "continue"

def need_fuzzy(state: AgentState) -> str:
    """Route to fuzzy node only when there are fuzzy matches to resolve."""
    return "fuzzy" if state.get("fuzzy_matches") else "skip"

def need_add_category_suggest(state: AgentState) -> str:
    """Route to suggestion node only when category came from LLM (not the user)."""
    # If the original message had a category parsed by LLM, fuzzy_input == stage_category.
    # We use a flag: if the original params.category was None we set a marker.
    # Simplest proxy: if fuzzy_matches is empty AND resolved_category == stage_category
    # the category was extracted or suggested. We handle the "no category in message"
    # case by checking whether the LLM provided the suggestion.
    # We store "_category_from_suggestion" in state to keep this clean.
    return "suggest" if state.get("_category_from_suggestion") else "skip"

def add_missing_done(state: AgentState) -> str:
    if state.get("intent") == "abort":
        return "abort"
    if state.get("stage_expense") is not None and state.get("stage_date") is not None:
        return "done"
    return "retry"

def update_id_done(state: AgentState) -> str:
    if state.get("intent") == "abort": return "abort"
    return "done" if state.get("stage_id") is not None else "retry"

def update_fields_done(state: AgentState) -> str:
    if state.get("intent") == "abort": return "abort"
    if any([state.get("resolved_category"),
            state.get("stage_expense"),
            state.get("stage_date")]):
        return "done"
    return "retry"

def delete_filter_done(state: AgentState) -> str:
    if state.get("intent") == "abort": return "abort"
    if any([state.get("resolved_category"),
            state.get("stage_date"),
            state.get("view_min") is not None,
            state.get("view_max") is not None]):
        return "done"
    return "retry"


# ═════════════════════════════════════════════════════════════════════════════
# GRAPH
# ═════════════════════════════════════════════════════════════════════════════

def build_graph():
    g = StateGraph(AgentState)

    # ── shared ────────────────────────────────────────────────────────────────
    g.add_node("router",      intent_router_node)

    # ── view ──────────────────────────────────────────────────────────────────
    g.add_node("view_extract",  view_extract_node)
    g.add_node("view_fuzzy",    fuzzy_node)
    g.add_node("view_execute",  view_execute_node)

    # ── add ───────────────────────────────────────────────────────────────────
    g.add_node("add_extract",        add_extract_node)
    g.add_node("add_fuzzy",          fuzzy_node)
    g.add_node("add_missing",        add_missing_node)
    g.add_node("add_confirm",        add_confirm_node)
    g.add_node("add_confirm_gate",   confirm_node)
    g.add_node("add_execute",        add_execute_node)

    # ── update ────────────────────────────────────────────────────────────────
    g.add_node("update_extract",       update_extract_node)
    g.add_node("update_id",            update_id_node)
    g.add_node("update_fuzzy",         fuzzy_node)
    g.add_node("update_fields",        update_fields_node)
    g.add_node("update_confirm",       update_confirm_node)
    g.add_node("update_confirm_gate",  confirm_node)
    g.add_node("update_execute",       update_execute_node)

    # ── delete ────────────────────────────────────────────────────────────────
    g.add_node("delete_extract",       delete_extract_node)
    g.add_node("delete_filter",        delete_filter_node)
    g.add_node("delete_fuzzy",         fuzzy_node)
    g.add_node("delete_confirm",       delete_confirm_node)
    g.add_node("delete_confirm_gate",  confirm_node)
    g.add_node("delete_execute",       delete_execute_node)

    # ── entry ─────────────────────────────────────────────────────────────────
    g.set_entry_point("router")
    g.add_conditional_edges("router", route_intent, {
        "router": "router",
        "view":   "view_extract",
        "add":    "add_extract",
        "update": "update_extract",
        "delete": "delete_extract",
    })

    # ── view flow ─────────────────────────────────────────────────────────────
    g.add_conditional_edges("view_extract", need_fuzzy, {
        "fuzzy": "view_fuzzy",
        "skip":  "view_execute",
    })
    g.add_edge("view_fuzzy",   "view_execute")
    g.add_edge("view_execute", END)

    # ── add flow ──────────────────────────────────────────────────────────────
    g.add_conditional_edges("add_extract", need_fuzzy, {
        "fuzzy": "add_fuzzy",
        "skip":  "add_missing",
    })
    g.add_edge("add_fuzzy", "add_missing")
    g.add_conditional_edges("add_missing", add_missing_done, {
        "done":  "add_confirm",
        "retry": "add_missing",
        "abort": END,
    })
    g.add_edge("add_confirm",      "add_confirm_gate")
    g.add_edge("add_confirm_gate", "add_execute")
    g.add_edge("add_execute",      END)

    # ── update flow ───────────────────────────────────────────────────────────
    g.add_edge("update_extract", "update_id")
    g.add_conditional_edges("update_id", update_id_done, {
        "done":  "update_fuzzy",
        "retry": "update_id",
        "abort": END,
    })
    g.add_conditional_edges("update_fuzzy", need_fuzzy, {
        "fuzzy": "update_fuzzy",
        "skip":  "update_fields",
    })
    g.add_edge("update_fuzzy", "update_fields")
    g.add_conditional_edges("update_fields", update_fields_done, {
        "done":  "update_confirm",
        "retry": "update_fields",
        "abort": END,
    })
    g.add_edge("update_confirm",      "update_confirm_gate")
    g.add_edge("update_confirm_gate", "update_execute")
    g.add_edge("update_execute",      END)

    # ── delete flow ───────────────────────────────────────────────────────────
    g.add_conditional_edges("delete_extract", delete_filter_done, {
        "done":  "delete_fuzzy",
        "retry": "delete_filter",
        "abort": END,
    })
    g.add_conditional_edges("delete_filter", delete_filter_done, {
        "done":  "delete_fuzzy",
        "retry": "delete_filter",
        "abort": END,
    })
    g.add_conditional_edges("delete_fuzzy", need_fuzzy, {
        "fuzzy": "delete_fuzzy",
        "skip":  "delete_confirm",
    })
    g.add_edge("delete_fuzzy",        "delete_confirm")
    g.add_edge("delete_confirm",      "delete_confirm_gate")
    g.add_edge("delete_confirm_gate", "delete_execute")
    g.add_edge("delete_execute",      END)

    return g.compile(checkpointer=MemorySaver())


def make_initial_state(username: str, user_input: str) -> AgentState:
    return {
        "messages": [{"role": "user", "content": user_input}],
        "username": username,
        "intent": "",
        "available_categories": [],
        "pending_action": "",
        "confirmed": False,
        "stage_category": None,
        "stage_expense": None,
        "stage_date": None,
        "stage_id": None,
        "fuzzy_input": None,
        "fuzzy_matches": [],
        "resolved_category": None,
        "view_min": None,
        "view_max": None,
        "retry_count": 0,
    }


def main(username: str):
    graph  = build_graph()
    config = {"configurable": {"thread_id": f"user-{username}"}}
    print(f"\n💰 Expense Tracker — logged in as {username!r}")
    print("   Type your request (or 'quit' to exit)\n")

    while True:
        snapshot = graph.get_state(config)
        if snapshot and snapshot.next:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if user_input.lower() in ("quit", "exit", "q"):
                break
            for _ in graph.stream(Command(resume=user_input), config=config, stream_mode="values"):
                pass
            continue

        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        initial = make_initial_state(username, user_input)
        for _ in graph.stream(initial, config=config, stream_mode="values"):
            pass


main(username="omar")