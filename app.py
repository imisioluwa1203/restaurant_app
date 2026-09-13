from flask import Flask, render_template
from restaurant import Orders, unavailable_food, add_order, remove_order, print_receipt
from  flask import Flask, render_template, request, redirect
from flask import Flask, render_template, request, redirect, session



app = Flask(__name__)
app.secret_key = 'acid-treats-secret-key' #needed for sessions to work



@app.route('/')
def home():
    return render_template('menu.html', orders=Orders)

@app.route('/add_order', methods=['POST'])
def add():
    food = request.form['food']
    quantity = int(request.form['quantity'])
    notes = request.form.get('notes', '').strip()
    add_order(food, quantity, notes)
    return redirect('/')

@app.route('/cart')
def cart():
    import restaurant
    return render_template('cart.html', ordered_food=restaurant.Ordered_food, total=restaurant.total_amount_ordered)


@app.route('/remove_order', methods=['POST'])
def remove():
    item = request.form['item']
    parts = item.split()
    quantity= int(parts[0])
    food = parts[1]
    remove_order(food, int(quantity))
    return redirect('/cart')

@app.route('/checkout')
def checkout():
    import restaurant
    return render_template('checkout.html', ordered_food=restaurant.Ordered_food, total=restaurant.total_amount_ordered)


@app.route('/place_order', methods=['POST'])
def place_order():
    import restaurant
    order_type = request.form.get('order_type', 'Pickup')

    order_record = {
        'items': list(restaurant.Ordered_food),
        'total': restaurant.total_amount_ordered,
        'type': order_type
    }

    if 'order_history' not in session:
        session['order_history'] = []
    session['order_history'].append(order_record)
    session.modified = True

    restaurant.Ordered_food.clear()
    restaurant.total_amount_ordered = 0
    return render_template('order_confirmed.html', order_type=order_type)

@app.route('/history')
def history():
    orders = session.get('order_history', [])
    return render_template('history.html', orders=orders)


if __name__ == '__main__':
    app.run(debug=True)

