import streamlit as st
from supabase import create_client, Client

# [내장 완료] 제공해주신 Supabase 연동 정보
SUPABASE_URL = "https://kktrkhfpxeavhaugzohd.supabase.co"
SUPABASE_KEY = "sb_publishable_c0dtskcvaF1CjK9fZwBm-g_XgRg6hXH"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

st.set_page_config(page_title="스마트 오답노트 마스터", layout="wide")

# 사이드바를 공통 영역으로 활용하여 사용자 정보를 상시 입력받음
with st.sidebar:
    st.header("👤 사용자 인증")
    # [핵심] 여러 사람이 쓸 때 누가 누군지 구분하는 고유 이름(아이디)
    user_name = st.text_input("내 이름(닉네임)을 입력하세요", value="홍길동").strip()
    
    st.divider()
    st.header("⚙️ 시험지 선택")
    exam_id = st.text_input("시험 이름을 입력하세요", value="2026년 3월 고3 수학", key="search_exam_id")

# 화면 상단 탭 3개 유지
tab1, tab2, tab3 = st.tabs([
    "📝 모의고사 채점하기", 
    "⚙️ 새 시험지 정답 등록하기", 
    "🔍 내가 쓴 오답노트 모아보기"
])

# ==========================================
# 탭 1: 모의고사 채점 및 취약점 분석 (개인별 오답 저장)
# ==========================================
with tab1:
    st.title("📊 취약점 분석 스마트 오답노트")
    st.caption(f"현재 **[{user_name}]** 님으로 접속 중입니다. 본인의 답안을 채점하세요.")

    if not user_name:
        st.error("⚠️ 사이드바에 이름을 입력해 주셔야 오답노트 저장이 가능합니다.")
        st.stop()

    questions_db = []
    try:
        res = supabase.table("questions").select("*").eq("exam_id", exam_id.strip()).execute()
        questions_db = res.data
    except Exception as e:
        st.error(f"DB 연결 오류: {e}")

    if questions_db:
        total_q = len(questions_db)
        st.success(f"📅 **{exam_id}** 시험지가 로드되었습니다. (총 {total_q}문항)")
    else:
        total_q = 20
        st.warning(f"⚠️ '{exam_id}'은(는) 아직 등록되지 않은 시험지입니다. [정답 등록하기] 탭에서 먼저 등록해 주세요.")

    st.subheader(f"✍️ 내 답안 마킹 (1번 ~ {total_q}번)")
    user_answers = {}

    num_rows = (total_q + 3) // 4
    for row in range(num_rows):
        cols = st.columns(4)
        for col_idx in range(4):
            q_num = row * 4 + col_idx + 1
            if q_num <= total_q:
                with cols[col_idx]:
                    user_answers[str(q_num)] = st.text_input(f"{q_num}번 답", key=f"q_{q_num}", value="")

    st.divider()

    if st.button("🚀 전 문항 일괄 채점 및 분석하기", type="primary"):
        if not questions_db:
            st.error("등록되지 않은 시험지는 채점할 수 없습니다.")
        else:
            with st.spinner("채점 중..."):
                wrong_questions = []
                correct_count = 0
                
                # [개선] 오답 노트를 불러올 때 '현재 로그인한 사용자(user_name)'의 데이터만 필터링해서 가져옴
                notes_res = supabase.table("wrong_notes").select("*").eq("exam_id", exam_id.strip()).eq("user_name", user_name).execute()
                saved_memos = {str(n["question_number"]): n["user_memo"] for n in notes_res.data}
                
                questions_db.sort(key=lambda x: x["question_number"])
                
                for q in questions_db:
                    q_num_str = str(q["question_number"])
                    user_ans = user_answers.get(q_num_str, "").strip()
                    correct_ans = str(q["answer"]).strip()
                    
                    if user_ans == correct_ans:
                        correct_count += 1
                    else:
                        wrong_questions.append({
                            "question_number": q["question_number"],
                            "correct_answer": correct_ans,
                            "user_answer": user_ans if user_ans else "(미제출)",
                            "concept_tags": q.get("concept_tags", []),
                            "saved_memo": saved_memos.get(q_num_str, "")
                        })
                
                score_str = f"{correct_count}/{total_q}"
                wrong_count = len(wrong_questions)
                
                st.success(f"💯 채점 완료! 내 성적: {score_str}")
                
                if wrong_count == 0:
                    st.balloons()
                    st.info("와우! 만점입니다! 🎉")
                else:
                    tag_counts = {}
                    for item in wrong_questions:
                        for tag in item['concept_tags']:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1
                    
                    if tag_counts:
                        st.subheader("📊 내 취약 개념 통계 분석")
                        st.bar_chart(tag_counts, horizontal=True)
                    
                    st.divider()
                    st.subheader(f"❌ 틀린 문제 오답 노트 ({wrong_count}문항)")
                    
                    for item in wrong_questions:
                        with st.container(border=True):
                            st.markdown(f"### ❓ {item['question_number']}번 문제")
                            st.markdown(f"**🏷️ 출제 개념:** {', '.join(item['concept_tags']) if item['concept_tags'] else '지정 없음'}")
                            st.error(f"내가 제출한 답: {item['user_answer']}  |  **실제 정답: {item['correct_answer']}**")
                            
                            user_memo = st.text_area("오답 메모", value=item['saved_memo'], key=f"input_{exam_id}_{item['question_number']}")
                            if st.button("💾 DB에 영구 저장하기", key=f"btn_{exam_id}_{item['question_number']}"):
                                # [개선] 저장할 때 누구의 오답노트인지 user_name을 같이 명시하여 저장
                                save_data = {
                                    "exam_id": exam_id.strip(), 
                                    "question_number": item['question_number'], 
                                    "user_name": user_name, 
                                    "user_memo": user_memo
                                }
                                supabase.table("wrong_notes").upsert(save_data, on_conflict="exam_id,question_number,user_name").execute()
                                st.toast(f"🎉 {item['question_number']}번 오답 메모가 [{user_name}]님 전용 공간에 저장되었습니다!")

# ==========================================
# 탭 2: 관리자용 [가변형 정답 등록기]
# ==========================================
with tab2:
    st.title("⚙️ 모의고사 정답 초고속 등록기")
    st.caption("과목별로 다른 시험 문제 수를 자유롭게 지정하여 등록할 수 있습니다. (정답지는 전 세계 공통입니다.)")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: reg_year = st.number_input("년도", value=2026, step=1)
    with col2: reg_month = st.number_input("월", value=3, step=1)
    with col3: reg_grade = st.selectbox("학년", ["고1", "고2", "고3"], index=2)
    with col4: reg_subject = st.text_input("과목", value="수학")
    with col5: reg_total_q = st.number_input("총 문항 수", value=20, min_value=1, max_value=100, step=1)

    reg_exam_id = f"{reg_year}년 {reg_month}월 {reg_grade} {reg_subject}"
    st.info(f"생성될 시험 이름: **{reg_exam_id}** (총 {reg_total_q}문항)")

    st.subheader("📋 정답 일괄 입력")
    st.caption(f"정확히 **{reg_total_q}개**의 정답을 띄어쓰기로 구분해서 입력해 주세요.")
    
    default_ans = " ".join(["1" if i%5==0 else "2" if i%5==1 else "3" if i%5==2 else "4" if i%5==3 else "5" for i in range(reg_total_q)])
    raw_answers = st.text_input("정답 입력창", value=default_ans)

    st.subheader("🏷️ 단원 개념 태그 입력")
    raw_tags = st.text_area("개념 태그 입력창 (쉼표 구분)", value="행렬,수열,방정식,미분,적분,함수,기하,확률,통계,로그,지수,삼각함수,수열의극한,함수의극한")

    if st.button("🔥 클릭 한 번으로 DB에 맞춤형 문항 일괄 등록", type="primary"):
        ans_list = raw_answers.strip().split()
        tag_list = [t.strip() for t in raw_tags.strip().split(",")]
        
        if len(ans_list) != reg_total_q:
            st.error(f"설정된 문항 수는 {reg_total_q}개인데, 입력된 정답은 {len(ans_list)}개입니다. 개수를 맞춰주세요!")
        else:
            with st.spinner("Supabase DB에 맞춤형 정답지 생성 중..."):
                try:
                    supabase.table("questions").delete().eq("exam_id", reg_exam_id).execute()
                    bulk_data = []
                    for i in range(reg_total_q):
                        tag_name = tag_list[i % len(tag_list)] if tag_list and tag_list[0] else "기본개념"
                        
                        row_data = {
                            "year": reg_year,
                            "month": reg_month,
                            "grade": reg_grade,
                            "subject": reg_subject,
                            "exam_id": reg_exam_id,
                            "question_number": i + 1,
                            "answer": ans_list[i],
                            "concept_tags": [tag_name]
                        }
                        bulk_data.append(row_data)
                    
                    supabase.table("questions").insert(bulk_data).execute()
                    st.balloons()
                    st.success(f"🎉 '{reg_exam_id}' ({reg_total_q}문항) 등록 성공!")
                except Exception as e:
                    st.error(f"등록 실패: {e}")

# ==========================================
# 탭 3: 내가 작성한 오답노트 보관함 (개인별 격리 복습)
# ==========================================
with tab3:
    st.title("🔍 내 손안의 오답노트 보관함")
    st.caption(f"현재 **[{user_name}]** 님이 클라우드 DB에 기록한 오답 기록만 필터링하여 보여줍니다.")

    # [개선] 전체가 아닌 '내 이름(user_name)'으로 등록된 오답 시험지 리스트만 쏙 골라옴
    try:
        exam_res = supabase.table("wrong_notes").select("exam_id").eq("user_name", user_name).execute()
        exam_list = list(set([n["exam_id"] for n in exam_res.data])) if exam_res.data else []
    except Exception as e:
        exam_list = []

    if not exam_list:
        st.info(f"💡 [{user_name}]님 이름으로 저장된 오답 메모가 아직 없습니다. 채점하기에서 메모를 먼저 작성해 보세요!")
    else:
        selected_exam = st.selectbox("복습할 시험지를 선택하세요", exam_list, key="select_review_exam")

        if selected_exam:
            with st.spinner("오답 기록장 가져오는 중..."):
                # [개선] 해당 시험 정보 중에서도 내 오답노트만 불러오기
                notes_res = supabase.table("wrong_notes").select("*").eq("exam_id", selected_exam).eq("user_name", user_name).execute()
                saved_notes = notes_res.data

                q_res = supabase.table("questions").select("*").eq("exam_id", selected_exam).execute()
                questions_dict = {q["question_number"]: q for q in q_res.data} if q_res.data else {}

                if not saved_notes:
                    st.info("이 시험지에는 저장된 오답 메모가 없습니다.")
                else:
                    st.subheader(f"📋 '{selected_exam}' 오답 복습 리스트 (총 {len(saved_notes)}문항)")
                    
                    saved_notes.sort(key=lambda x: x["question_number"])

                    for note in saved_notes:
                        q_num = note["question_number"]
                        q_info = questions_dict.get(q_num, {})
                        concept = ", ".join(q_info.get("concept_tags", [])) if q_info.get("concept_tags") else "기본개념"
                        correct_ans = q_info.get("answer", "알 수 없음")

                        with st.container(border=True):
                            st.markdown(f"### ❓ {q_num}번 문제")
                            st.markdown(f"**🏷️ 출제 개념:** `{concept}`   |   **🎯 실제 정답:** `{correct_ans}`")
                            
                            new_memo = st.text_area(
                                "✍️ 내가 적었던 오답 기록", 
                                value=note["user_memo"], 
                                key=f"review_{selected_exam}_{q_num}"
                            )

                            col1, col2 = st.columns([1, 8])
                            with col1:
                                if st.button("📝 수정", key=f"edit_btn_{selected_exam}_{q_num}"):
                                    supabase.table("wrong_notes").upsert({
                                        "exam_id": selected_exam,
                                        "question_number": q_num,
                                        "user_name": user_name,
                                        "user_memo": new_memo
                                    }, on_conflict="exam_id,question_number,user_name").execute()
                                    st.toast("💡 오답 메모가 수정되었습니다!")
                            with col2:
                                if st.button("🗑️ 삭제", key=f"del_btn_{selected_exam}_{q_num}"):
                                    supabase.table("wrong_notes").delete().eq("exam_id", selected_exam).eq("question_number", q_num).eq("user_name", user_name).execute()
                                    st.toast("🗑️ 오답 메모가 삭제되었습니다.")
                                    st.rerun()