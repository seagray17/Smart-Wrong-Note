import streamlit as st
import json
import bcrypt
import logging
from urllib.request import Request, urlopen
from supabase import create_client, Client

# 로깅 설정 (침묵하는 에러 방지 및 디버깅용)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔒 안전하게 Streamlit Secrets에서 환경변수 로드
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    DISCORD_WEBHOOK_URL = st.secrets["DISCORD_WEBHOOK_URL"]
except KeyError as e:
    st.error(f"❌ 필수 Secrets 설정이 누락되었습니다: {e}")
    st.stop()

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()
st.set_page_config(page_title="스마트 오답노트 마스터", layout="wide")

# 🔒 강력한 Bcrypt 비밀번호 암호화 및 검증 함수
def hash_password(password: str) -> str:
    # bcrypt는 알아서 Salt를 생성하여 해싱하므로 레인보우 테이블 공격을 방어합니다.
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        logger.error(f"비밀번호 검증 중 오류: {e}")
        return False

# 디스코드 알림 함수 (에러 핸들링 및 로그 기록 강화)
def send_discord_notification(name, text):
    if not DISCORD_WEBHOOK_URL or "YOUR_WEBHOOK" in DISCORD_WEBHOOK_URL: 
        return
    payload = {
        "embeds": [{
            "title": "✉️ 새로운 개발자 피드백!", 
            "color": 5814783, 
            "fields": [
                {"name": "👤 작성자", "value": name, "inline": True}, 
                {"name": "✍️ 내용", "value": text, "inline": False}
            ]
        }]
    }
    try:
        req = Request(DISCORD_WEBHOOK_URL, data=json.dumps(payload).encode('utf-8'))
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urlopen(req) as response: 
            if response.status != 204 and response.status != 200:
                logger.warning(f"디스코드 웹훅 응답 이상 상태코드: {response.status}")
    except Exception as e: 
        # except: pass 를 제거하고 서버에 로그를 남겨 추적 가능하게 변경
        logger.error(f"디스코드 웹훅 전송 실패: {e}")

# Session State 초기화 (로그인 상태 및 권한 관리)
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "user_role" not in st.session_state:
    st.session_state["user_role"] = "user"  # 기본 권한 설정

# 사이드바 레이아웃
with st.sidebar:
    st.header("👤 회원 시스템")
    
    if not st.session_state["logged_in"]:
        auth_mode = st.radio("모드를 선택하세요", ["로그인", "회원가입"])
        input_name = st.text_input("이름(닉네임)", value="").strip()
        input_password = st.text_input("비밀번호", value="", type="password").strip()
        
        if auth_mode == "회원가입":
            if st.button("📝 회원가입 하기", use_container_width=True):
                if not input_name or not input_password:
                    st.error("이름과 비밀번호를 모두 입력해주세요.")
                else:
                    try:
                        user_check = supabase.table("users").select("*").eq("user_name", input_name).execute()
                        if user_check.data:
                            st.error("이미 존재하는 이름입니다. 다른 이름을 사용해주세요.")
                        else:
                            supabase.table("users").insert({
                                "user_name": input_name,
                                "password_hash": hash_password(input_password),
                                "role": "user" # 기본적으로 모든 가입자는 일반 유저
                            }).execute()
                            st.success("🎉 회원가입 성공! 로그인 모드로 변경해 접속하세요.")
                    except Exception as e:
                        st.error("회원가입 처리 중 오류가 발생했습니다.")
                        logger.error(f"회원가입 실패 원인: {e}")
                        
        elif auth_mode == "로그인":
            if st.button("🔒 로그인 하기", use_container_width=True):
                if not input_name or not input_password:
                    st.error("이름과 비밀번호를 입력해주세요.")
                else:
                    try:
                        user_res = supabase.table("users").select("*").eq("user_name", input_name).execute()
                        if user_res.data and check_password(input_password, user_res.data[0]["password_hash"]):
                            st.session_state["logged_in"] = True
                            st.session_state["username"] = input_name
                            st.session_state["user_role"] = user_res.data[0].get("role", "user") # DB에서 권한 로드
                            st.success(f"👋 {input_name}님 환영합니다!")
                            st.rerun()
                        else:
                            st.error("이름 또는 비밀번호가 올바르지 않습니다.")
                    except Exception as e:
                        st.error("로그인 처리 중 오류가 발생했습니다.")
                        logger.error(f"로그인 실패 원인: {e}")
    else:
        role_badge = "👑 관리자" if st.session_state["user_role"] == "admin" else "👤 일반회원"
        st.success(f"🟢 {st.session_state['username']} 님 ({role_badge})")
        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.session_state["user_role"] = "user"
            st.session_state["show_wrong_notes"] = False
            st.rerun()

    st.divider()
    st.header("⚙️ 시험지 선택")
    exam_id = st.text_input("시험 이름 입력", value="2026년 3월 고3 수학", key="search_exam_id")
    st.divider()
    st.header("✉️ 개발자에게 한마디")
    with st.form(key="feedback_form", clear_on_submit=True):
        feedback_text = st.text_area("피드백 내용", max_chars=500)
        if st.form_submit_button("🚀 피드백 전송", use_container_width=True):
            if feedback_text.strip():
                sender = st.session_state["username"] if st.session_state["logged_in"] else "익명"
                try:
                    supabase.table("feedbacks").insert({"user_name": sender, "content": feedback_text.strip()}).execute()
                    send_discord_notification(sender, feedback_text.strip())
                    st.success("💖 피드백 전달 완료!")
                except Exception as e: 
                    st.error("피드백 전송에 실패했습니다.")
                    logger.error(f"피드백 DB 저장 실패: {e}")

# 비로그인 유저 차단 접근 제어
if not st.session_state["logged_in"]:
    st.title("📊 스마트 오답노트 마스터")
    st.info("💡 서비스를 이용하시려면 왼쪽 사이드바에서 **로그인**을 진행해 주세요.")
    st.stop()

user_name = st.session_state["username"]

# 권한에 따른 탭 구성 (관리자 권한인 'admin'일 때만 정답 등록 탭이 보임)
tabs_list = ["📝 모의고사 채점하기", "🔍 내가 쓴 오답노트 모아보기"]
if st.session_state["user_role"] == "admin":
    tabs_list.insert(1, "⚙️ 새 시험지 정답 등록하기")

tabs = st.tabs(tabs_list)

# 관리자 여부에 따라 인덱스 바인딩 매핑
tab_marking = tabs[0]
tab_register = tabs[1] if st.session_state["user_role"] == "admin" else None
tab_folder = tabs[2] if st.session_state["user_role"] == "admin" else tabs[1]

# ==========================================
# 탭 1: 채점 및 오답노트
# ==========================================
with tab_marking:
    st.title("📊 스마트 오답노트 채점기")
    
    questions_db = []
    try: 
        res = supabase.table("questions").select("*").eq("exam_id", exam_id.strip()).execute()
        questions_db = res.data
    except Exception as e: 
        st.error("시험지 데이터를 불러오지 못했습니다.")
        logger.error(f"Questions 조회 실패: {e}")

    if questions_db: st.success(f"📅 **{exam_id}** 시험지 로드 완료 (총 {len(questions_db)}문항)")
    else: st.warning(f"⚠️ '{exam_id}'은(는) 아직 등록되지 않은 시험지입니다.")

    with st.form(key="marking_form"):
        st.subheader("✍️ 내 답안 마킹")
        user_answers = {}
        total_q = len(questions_db) if questions_db else 20
        num_rows = (total_q + 3) // 4
        for row in range(num_rows):
            cols = st.columns(4)
            for col_idx in range(4):
                q_num = row * 4 + col_idx + 1
                if q_num <= total_q:
                    with cols[col_idx]: user_answers[str(q_num)] = st.text_input(f"{q_num}번 답", key=f"q_{q_num}")
        submit_marking = st.form_submit_button("🚀 전 문항 일괄 채점하기", type="primary")

    if submit_marking or st.session_state.get("show_wrong_notes", False):
        st.session_state["show_wrong_notes"] = True
        if not questions_db: st.error("등록되지 않은 시험지입니다.")
        else:
            wrong_questions = []
            correct_count = 0
            try:
                notes_res = supabase.table("wrong_notes").select("*").eq("exam_id", exam_id.strip()).eq("user_name", user_name).execute()
                saved_memos = {str(n["question_number"]): n["user_memo"] for n in notes_res.data}
            except Exception as e:
                saved_memos = {}
                logger.error(f"Wrong_notes 조회 실패: {e}")
                
            questions_db.sort(key=lambda x: x["question_number"])
            
            for q in questions_db:
                q_num_str = str(q["question_number"])
                user_ans = user_answers.get(q_num_str, "").strip()
                correct_ans = str(q["answer"]).strip()
                if user_ans == correct_ans: correct_count += 1
                else: wrong_questions.append({"question_number": q["question_number"], "correct_answer": correct_ans, "user_answer": user_ans if user_ans else "(미제출)", "saved_memo": saved_memos.get(q_num_str, "")})
            
            st.success(f"💯 내 성적: {correct_count}/{len(questions_db)}")
            if len(wrong_questions) == 0: st.balloons()
            else:
                for item in wrong_questions:
                    with st.form(key=f"wrong_note_form_{item['question_number']}"):
                        st.markdown(f"### ❓ {item['question_number']}번 문제 (정답: {item['correct_answer']})")
                        user_memo = st.text_area("오답 메모", value=item['saved_memo'], key=f"memo_{item['question_number']}")
                        if st.form_submit_button("💾 오답 저장"):
                            try:
                                check_res = supabase.table("wrong_notes").select("*").eq("exam_id", exam_id.strip()).eq("question_number", str(item['question_number'])).eq("user_name", user_name).execute()
                                if check_res.data: 
                                    supabase.table("wrong_notes").update({"user_memo": user_memo}).eq("exam_id", exam_id.strip()).eq("question_number", str(item['question_number'])).eq("user_name", user_name).execute()
                                else: 
                                    supabase.table("wrong_notes").insert({"exam_id": exam_id.strip(), "question_number": str(item['question_number']), "user_name": user_name, "password": "", "user_memo": user_memo}).execute()
                                st.toast("저장 완료!")
                            except Exception as e: 
                                st.error("오답 저장에 실패했습니다.")
                                logger.error(f"오답 저장 에러: {e}")

# ==========================================
# 탭 2: 관리자용 [정답 일괄 등록기] (조건부 노출)
# ==========================================
if tab_register:
    with tab_register:
        st.title("⚙️ 모의고사 정답 초고속 등록기")
        st.success("👑 관리자 인증 유저만 접근 가능한 공간입니다.")
        
        with st.form(key="register_form"):
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1: reg_year = st.number_input("년도", value=2026, step=1)
            with col2: reg_month = st.number_input("월", value=3, step=1)
            with col3: reg_grade = st.selectbox("학년", ["고1", "고2", "고3"], index=2)
            with col4: reg_subject = st.text_input("과목", value="수학")
            with col5: reg_total_q = st.number_input("총 문항 수", value=20, min_value=1, max_value=100, step=1)

            st.subheader("📋 정답 일괄 입력")
            default_ans = " ".join(["1" if i%5==0 else "2" if i%5==1 else "3" if i%5==2 else "4" if i%5==3 else "5" for i in range(20)])
            raw_answers = st.text_input("정답 입력창 (숫자들을 공백으로 구분해서 입력하세요)", value=default_ans)

            submit_registration = st.form_submit_button("🔥 클릭 한 번으로 DB에 맞춤형 문항 일괄 등록", type="primary")

        if submit_registration:
            reg_exam_id = f"{reg_year}년 {reg_month}월 {reg_grade} {reg_subject}"
            ans_list = raw_answers.strip().split()
            
            if len(ans_list) != reg_total_q:
                st.error(f"설정된 문항 수는 {reg_total_q}개인데, 입력된 정답은 {len(ans_list)}개입니다.")
            else:
                with st.spinner("Supabase DB에 정답지 생성 중..."):
                    try:
                        supabase.table("questions").delete().eq("exam_id", reg_exam_id).execute()
                        bulk_data = []
                        for i in range(reg_total_q):
                            bulk_data.append({
                                "year": reg_year, "month": reg_month, "grade": reg_grade, "subject": reg_subject,
                                "exam_id": reg_exam_id, "question_number": i + 1, "answer": ans_list[i], "concept_tags": [] 
                            })
                        
                        supabase.table("questions").insert(bulk_data).execute()
                        st.balloons()
                        st.success(f"🎉 '{reg_exam_id}' 등록 성공!")
                    except Exception as e:
                        st.error("정답 등록에 실패했습니다.")
                        logger.error(f"정답 일괄 등록 에러: {e}")

# ==========================================
# 탭 3: 오답노트 보관함
# ==========================================
with tab_folder:
    st.title("🔍 내 손안의 오답노트 보관함")
    try:
        exam_res = supabase.table("wrong_notes").select("exam_id").eq("user_name", user_name).execute()
        exam_list = list(set([n["exam_id"].strip() for n in exam_res.data])) if exam_res.data else []
    except Exception as e: 
        exam_list = []
        logger.error(f"보관함 시험지 리스트 조회 실패: {e}")

    if not exam_list: st.info("일치하는 오답 메모가 없습니다.")
    else:
        selected_exam = st.selectbox("복습할 시험지 선택", exam_list)
        if selected_exam:
            try:
                notes_res = supabase.table("wrong_notes").select("*").eq("exam_id", selected_exam.strip()).eq("user_name", user_name).execute()
                q_res = supabase.table("questions").select("*").eq("exam_id", selected_exam.strip()).execute()
                questions_dict = {str(q["question_number"]).strip(): q for q in q_res.data} if q_res.data else {}

                for note in notes_res.data:
                    q_num_str = str(note["question_number"]).strip()
                    correct_ans = questions_dict.get(q_num_str, {}).get("answer", "알 수 없음")
                    with st.form(key=f"review_{q_num_str}"):
                        st.markdown(f"### ❓ {q_num_str}번 문제 (정답: `{correct_ans}`)")
                        new_memo = st.text_area("오답 기록 수정", value=note["user_memo"])
                        c1, c2, _ = st.columns([1, 1, 8])
                        with c1:
                            if st.form_submit_button("📝 수정"):
                                supabase.table("wrong_notes").update({"user_memo": new_memo}).eq("exam_id", selected_exam.strip()).eq("question_number", q_num_str).eq("user_name", user_name).execute()
                                st.rerun()
                        with c2:
                            if st.form_submit_button("🗑️ 삭제"):
                                supabase.table("wrong_notes").delete().eq("exam_id", selected_exam.strip()).eq("question_number", q_num_str).eq("user_name", user_name).execute()
                                st.rerun()
            except Exception as e:
                st.error("오답노트를 불러오는 과정에서 오류가 발생했습니다.")
                logger.error(f"오답노트 상세 로드 에러: {e}")