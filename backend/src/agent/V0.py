from __future__ import annotations


from dotenv import load_dotenv
load_dotenv()


import sys
from typing import Literal, Optional
from datetime import date

from pydantic import BaseModel,field_validator
from typing_extensions import TypedDict

from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from rapidfuzz import process as fuzz_process


from backend.src.feature.filter_and_show import filter_expenses
from backend.src.feature.add_values import add_values
from backend.src.feature.update_values import update_values
from backend.src.feature.delete_record import delete_record
from backend.src.feature.get_categories import get_categories

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_NAME      = "llama-3.3-70b-versatile"   # swap to any Groq-hosted model
DB_LOCATION     = "backend/database/database.db"
MAX_RETRIES     = 3
FUZZY_THRESHOLD = 90

# ── LLM ───────────────────────────────────────────────────────────────────────
llm = ChatGroq(model=MODEL_NAME, temperature=0)

# ── State ─────────────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: list
    intent: str
    extracted_params: dict
    pending_category: str | None
    category_source: str
    pending_action: str
    awaiting_human: bool
    turn_count: int
    username: str

# ── Pydantic extraction models ────────────────────────────────────────────────
class IntentResult(BaseModel):
    intent: Literal["view", "add", "update", "delete", "clarify"]
    reason: str

class ViewParams(BaseModel):
    category: Optional[str] = None
    date: Optional[str] = None
    min_expense: Optional[float] = None
    max_expense: Optional[float] = None

class AddParams(BaseModel):
    category: Optional[str] = None
    expense: Optional[float] = None
    date: Optional[date] = None

class UpdateParams(BaseModel):
    id: Optional[int] = None
    category: Optional[str] = None
    expense: Optional[float] = None
    date: Optional[str] = None

class DeleteParams(BaseModel):
    category: Optional[str] = None
    date: Optional[str] = None
    min_expense: Optional[float] = None
    max_expense: Optional[float] = None

# ── Utility ───────────────────────────────────────────────────────────────────
def fuzzy_match(input_category: str, existing_categories: list[str]) -> list[tuple[str, int]]:
    """Return categories matching above FUZZY_THRESHOLD, sorted by score desc."""
    if not existing_categories:
        return []
    normalized = input_category.lower().strip()
    results = fuzz_process.extract(normalized, [c.lower().strip() for c in existing_categories])
    return [(name, score) for name, score, _ in results if score >= FUZZY_THRESHOLD]

def fmt_expenses(rows: list[dict]) -> str:
    """Format a list of expense dicts into a readable table."""
    if not rows:
        return "(none)"
    lines = ["  ID | Category     | Amount  | Date"]
    lines.append("  " + "-" * 42)
    for r in rows:
        lines.append(f"  {r['id']:>3} | {r['category']:<12} | {r['expense']:>7.2f} | {r['date']}")
    return "\n".join(lines)

def say(msg: str):
    """Print agent output."""
    print(f"\n🤖 {msg}\n")

# ── Nodes ─────────────────────────────────────────────────────────────────────

def intent_router_node(state: AgentState) -> AgentState:
    """Classify the user's latest message into an intent."""
    extractor = llm.with_structured_output(IntentResult)
    user_msg = state["messages"][-1]["content"]
    result: IntentResult = extractor.invoke(
        f"Classify the user's intent for an expense tracker app.\n"
        f"Intents: view, add, update, delete, clarify (if ambiguous).\n"
        f"User said: {user_msg}"
    )
    if result.intent == "clarify":
        say(f"Could you clarify? {result.reason}")
        new_input = interrupt("Waiting for clarification")
        state["messages"].append({"role": "user", "content": new_input})
    return {**state, "intent": result.intent}


def get_categories_node(state: AgentState) -> AgentState:
    """Fetch distinct categories for the current user from the DB."""
    try:
        cats = get_categories(DB_LOCATION, state["username"])
    except Exception:
        cats = []
    params = state.get("extracted_params", {})
    params["available_categories"] = cats
    return {**state, "extracted_params": params}


def _ask_fuzzy_approval(input_cat: str, matches: list[tuple[str, int]]) -> str:
    """Show fuzzy matches, ask user to pick or keep their own. Returns resolved category."""
    if len(matches) == 1:
        matched, score = matches[0]
        say(f'Did you mean "{matched}" (similarity {score})? Reply "yes" to use it or type a different category.')
        answer = interrupt("Fuzzy single match approval")
        return matched if answer.strip().lower() in ("yes", "y") else answer.strip().lower()
    else:
        options = "\n".join(f"  {i+1}. {m} ({s}%)" for i, (m, s) in enumerate(matches))
        say(f'Found similar categories:\n{options}\nType a number to pick one, or type your own category.')
        answer = interrupt("Fuzzy multi match selection")
        try:
            idx = int(answer.strip()) - 1
            if 0 <= idx < len(matches):
                return matches[idx][0]
        except ValueError:
            pass
        return answer.strip().lower()


def confirmation_node(state: AgentState) -> AgentState:
    """Show pending_action to user and wait for yes/no confirmation."""
    say(f"About to do:\n  {state['pending_action']}\nConfirm? (yes/no)")
    answer = interrupt("Confirmation")
    confirmed = answer.strip().lower() in ("yes", "y")
    params = state.get("extracted_params", {})
    params["confirmed"] = confirmed
    return {**state, "extracted_params": params}


def view_node(state: AgentState) -> AgentState:
    """Fetch and display expenses, with optional filters extracted from the user message."""
    state = get_categories_node(state)
    user_msg = state["messages"][-1]["content"]
    extractor = llm.with_structured_output(ViewParams)
    params: ViewParams = extractor.invoke(
        f"Extract view/filter parameters from: {user_msg}\n"
        f"Available categories: {state['extracted_params'].get('available_categories', [])}"
    )

    category = params.category
    if category:
        matches = fuzzy_match(category, state["extracted_params"].get("available_categories", []))
        if matches:
            category = _ask_fuzzy_approval(category, matches)

    try:
        rows = filter_expenses(DB_LOCATION, state["username"], category, params.date,
                               params.min_expense, params.max_expense)
        if rows:
            say(f"Found {len(rows)} expense(s):\n{fmt_expenses(rows)}")
        else:
            say("No expenses found matching your filters.")
    except Exception as e:
        say("Something went wrong fetching your expenses. Please try again.")

    return {**state, "intent": ""}


def add_node(state: AgentState) -> AgentState:
    """Collect category, expense, and date; confirm; then insert a new expense record."""
    state = get_categories_node(state)
    available = state["extracted_params"].get("available_categories", [])
    user_msg = state["messages"][-1]["content"]
    extractor = llm.with_structured_output(AddParams)

    params: AddParams = extractor.invoke(
        f"Extract expense details (category, amount, date YYYY-MM-DD) from: {user_msg}\n"
        f"Existing categories for context: {available}"
    )

    # ── Resolve category ──────────────────────────────────────────────────────
    if params.category:
        category_source = "user"
        matches = fuzzy_match(params.category, available)
        category = _ask_fuzzy_approval(params.category, matches) if matches else params.category.lower()
    else:
        category_source = "agent"
        # LLM suggests a category
        suggestion = llm.invoke(
            f"Suggest a short expense category (1-2 words) for: {user_msg}\n"
            f"Existing: {available}. Reply with the category name only."
        ).content.strip().lower()
        say(f'I suggest category "{suggestion}". Type "yes" to accept or enter your own.')
        answer = interrupt("Category suggestion approval")
        category = suggestion if answer.strip().lower() in ("yes", "y") else answer.strip().lower()

    # ── Collect missing fields ─────────────────────────────────────────────────
    expense = params.expense
    exp_date = str(params.date) if params.date else None
    turn = 0

    while (expense is None or exp_date is None) and turn < MAX_RETRIES:
        missing = []
        if expense is None:
            missing.append("amount")
        if exp_date is None:
            missing.append("date (YYYY-MM-DD)")
        say(f"Please provide: {', '.join(missing)}")
        extra = interrupt("Missing add fields")
        state["messages"].append({"role": "user", "content": extra})
        fill: AddParams = extractor.invoke(f"Extract from: {extra}")
        if fill.expense is not None:
            expense = fill.expense
        if fill.date is not None:
            exp_date = str(fill.date)
        turn += 1

    if expense is None or exp_date is None:
        say("I wasn't able to complete this — please try rephrasing your request.")
        return {**state, "intent": ""}

    # ── Confirm & execute ─────────────────────────────────────────────────────
    state["pending_action"] = f'Add expense: {category} | £{expense:.2f} | {exp_date}'
    state = confirmation_node(state)
    if not state["extracted_params"].get("confirmed"):
        say("Cancelled.")
        return {**state, "intent": ""}

    try:
        result = add_values(state["username"], category, expense, exp_date, DB_LOCATION)
        say(result["message"])
    except ValueError as e:
        say("Could not add expense. Please try again.")

    return {**state, "intent": ""}


def update_node(state: AgentState) -> AgentState:
    """Find the target expense by ID, collect changes, confirm, then update."""
    state = get_categories_node(state)
    available = state["extracted_params"].get("available_categories", [])
    user_msg = state["messages"][-1]["content"]
    extractor = llm.with_structured_output(UpdateParams)

    params: UpdateParams = extractor.invoke(f"Extract update parameters from: {user_msg}")

    # ── Resolve ID ────────────────────────────────────────────────────────────
    turn = 0
    while params.id is None and turn < MAX_RETRIES:
        rows = filter_expenses(DB_LOCATION, state["username"])
        say(f"Which expense do you want to update? Here are yours:\n{fmt_expenses(rows)}\nProvide the ID:")
        answer = interrupt("Update ID selection")
        state["messages"].append({"role": "user", "content": answer})
        refill: UpdateParams = extractor.invoke(f"Extract update parameters from: {answer}")
        if refill.id is not None:
            params = refill
        turn += 1

    if params.id is None:
        say("I wasn't able to complete this — please try rephrasing your request.")
        return {**state, "intent": ""}

    # ── At least one change field ─────────────────────────────────────────────
    turn = 0
    while params.category is None and params.expense is None and params.date is None and turn < MAX_RETRIES:
        say("What would you like to change? (category, amount, or date)")
        answer = interrupt("Update fields")
        state["messages"].append({"role": "user", "content": answer})
        refill = extractor.invoke(f"Extract update parameters from: {answer}")
        params.category = refill.category or params.category
        params.expense  = refill.expense  or params.expense
        params.date     = refill.date     or params.date
        turn += 1

    # ── Fuzzy match new category ───────────────────────────────────────────────
    new_cat = params.category
    if new_cat:
        matches = fuzzy_match(new_cat, available)
        if matches:
            new_cat = _ask_fuzzy_approval(new_cat, matches)

    changes = []
    if new_cat:     changes.append(f"category → {new_cat}")
    if params.expense: changes.append(f"amount → {params.expense:.2f}")
    if params.date:    changes.append(f"date → {params.date}")

    state["pending_action"] = f"Update expense #{params.id}: {', '.join(changes)}"
    state = confirmation_node(state)
    if not state["extracted_params"].get("confirmed"):
        say("Cancelled.")
        return {**state, "intent": ""}

    try:
        result = update_values(DB_LOCATION, params.id, state["username"], new_cat, params.expense, params.date)
        say(f"Updated expense #{result['updated_id']}. Changes: {result['changes']}")
    except ValueError:
        say(f"Could not find expense #{params.id} for your account.")

    return {**state, "intent": ""}


def delete_node(state: AgentState) -> AgentState:
    """Filter expenses matching criteria, preview them, confirm, then delete."""
    state = get_categories_node(state)
    available = state["extracted_params"].get("available_categories", [])
    user_msg = state["messages"][-1]["content"]
    extractor = llm.with_structured_output(DeleteParams)

    params: DeleteParams = extractor.invoke(f"Extract delete filter parameters from: {user_msg}")

    # ── At least one filter ───────────────────────────────────────────────────
    turn = 0
    while not any([params.category, params.date, params.min_expense is not None, params.max_expense is not None]) and turn < MAX_RETRIES:
        say("Please provide at least one filter (category, date, min/max amount):")
        answer = interrupt("Delete filter")
        state["messages"].append({"role": "user", "content": answer})
        params = extractor.invoke(f"Extract delete filter parameters from: {answer}")
        turn += 1

    if not any([params.category, params.date, params.min_expense is not None, params.max_expense is not None]):
        say("I wasn't able to complete this — please try rephrasing your request.")
        return {**state, "intent": ""}

    # ── Fuzzy match category ───────────────────────────────────────────────────
    if params.category:
        matches = fuzzy_match(params.category, available)
        if matches:
            params.category = _ask_fuzzy_approval(params.category, matches)

    # ── Preview ───────────────────────────────────────────────────────────────
    try:
        preview = filter_expenses(DB_LOCATION, state["username"], params.category,
                                  params.date, params.min_expense, params.max_expense)
    except Exception:
        say("Something went wrong fetching expenses. Please try again.")
        return {**state, "intent": ""}

    if not preview:
        say("No matching expenses found.")
        return {**state, "intent": ""}

    state["pending_action"] = f"Delete {len(preview)} expense(s):\n{fmt_expenses(preview)}"
    state = confirmation_node(state)
    if not state["extracted_params"].get("confirmed"):
        say("Cancelled.")
        return {**state, "intent": ""}

    try:
        result = delete_record(DB_LOCATION, state["username"], params.category,
                               params.date, params.min_expense, params.max_expense)
        say(f"{result['message']} IDs: {result['deleted_ids']}")
    except Exception:
        say("Could not delete expenses. Please try again.")

    return {**state, "intent": ""}


# ── Graph ─────────────────────────────────────────────────────────────────────

def route_intent(state: AgentState) -> str:
    return state.get("intent", "view") or END

def build_graph():
    g = StateGraph(AgentState)
    g.add_node("router",  intent_router_node)
    g.add_node("view",    view_node)
    g.add_node("add",     add_node)
    g.add_node("update",  update_node)
    g.add_node("delete",  delete_node)

    g.set_entry_point("router")
    g.add_conditional_edges("router", route_intent, {
        "view":   "view",
        "add":    "add",
        "update": "update",
        "delete": "delete",
    })
    for node in ("view", "add", "update", "delete"):
        g.add_edge(node, END)

    return g.compile(checkpointer=MemorySaver())


# ── Main REPL ─────────────────────────────────────────────────────────────────

def main(username: str):
    graph = build_graph()
    config = {"configurable": {"thread_id": f"user-{username}"}}
    print(f"\n💰 Expense Tracker — logged in as {username!r}")
    print("   Type your request (or 'quit' to exit)\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        initial_state: AgentState = {
            "messages": [{"role": "user", "content": user_input}],
            "intent": "",
            "extracted_params": {},
            "pending_category": None,
            "category_source": "user",
            "pending_action": "",
            "awaiting_human": False,
            "turn_count": 0,
            "username": username,
        }

        # Stream the graph, handling interrupts (human-in-the-loop)
        for event in graph.stream(initial_state, config=config, stream_mode="values"):
            pass  # state updates handled inside nodes via interrupt()


main(username='omar')